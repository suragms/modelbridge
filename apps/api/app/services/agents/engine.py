"""Agent execution engine with multi-step tool loop and resource limits."""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, AgentExecution, AgentStep, AgentStatus, ExecutionStatus
from app.models.governance import ApprovalRequest, ApprovalStatus
from app.models.user import User
from app.schemas.chat import ChatCompletionRequest, ChatMessage
from app.services.agents.memory import MemoryStore
from app.services.agents.state import assert_transition, can_transition
from app.services.agents.tools import (
    execute_builtin,
    get_builtin,
    list_builtin_names,
    risk_requires_approval,
)
from app.services.audit import AuditService
from app.services.gateway import execute_chat
from app.services.metrics import record_agent_execution, record_agent_step, record_agent_tool_call

logger = structlog.get_logger()

AUDIT_AGENT_EXECUTION_STARTED = "agent.execution_started"
AUDIT_AGENT_EXECUTION_COMPLETED = "agent.execution_completed"
AUDIT_AGENT_EXECUTION_FAILED = "agent.execution_failed"
AUDIT_AGENT_TOOL_EXECUTED = "agent.tool_executed"


class ExecutionLimitError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


class AgentExecutionEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def transition(
        self,
        execution: AgentExecution,
        new_status: str,
        *,
        error_message: str | None = None,
        error_code: str | None = None,
    ) -> None:
        assert_transition(execution.status, new_status)
        execution.status = new_status
        if error_message:
            execution.error_message = error_message
        if error_code:
            execution.error_code = error_code
        if new_status in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.TIMED_OUT,
        }:
            execution.completed_at = datetime.now(UTC)
        await self.db.flush()

    async def _check_limits(self, agent: Agent, execution: AgentExecution, started_at: float) -> None:
        if execution.current_step >= agent.max_steps:
            raise ExecutionLimitError("MAX_STEPS", "Maximum step limit reached")
        elapsed = time.time() - started_at
        if elapsed > agent.timeout_seconds:
            raise ExecutionLimitError("TIMEOUT", "Execution timeout exceeded")
        if agent.max_tokens and execution.total_tokens >= agent.max_tokens:
            raise ExecutionLimitError("MAX_TOKENS", "Maximum token limit reached")
        if agent.max_budget_usd is not None and execution.estimated_cost_usd is not None:
            if execution.estimated_cost_usd >= agent.max_budget_usd:
                raise ExecutionLimitError("MAX_BUDGET", "Maximum budget limit reached")

    async def _refresh_execution(self, execution_id: uuid.UUID) -> AgentExecution:
        result = await self.db.execute(
            select(AgentExecution).where(AgentExecution.id == execution_id)
        )
        execution = result.scalar_one()
        await self.db.refresh(execution)
        return execution

    def _allowed_tools(self, agent: Agent) -> list[str]:
        cfg = agent.tool_configuration or {}
        allowed = cfg.get("allowed_tools")
        if allowed:
            return [t for t in allowed if t in list_builtin_names()]
        return list_builtin_names()

    def _tool_schemas(self, agent: Agent) -> list[dict]:
        schemas: list[dict] = []
        for name in self._allowed_tools(agent):
            tool = get_builtin(name)
            if tool:
                schemas.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.input_schema,
                        },
                    }
                )
        return schemas

    async def _record_step(
        self,
        execution: AgentExecution,
        *,
        step_number: int,
        step_type: str,
        model: str | None = None,
        provider: str | None = None,
        tool_name: str | None = None,
        latency_ms: float | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float | None = None,
        metadata: dict | None = None,
        status: str = "completed",
    ) -> AgentStep:
        step = AgentStep(
            execution_id=execution.id,
            organization_id=execution.organization_id,
            step_number=step_number,
            step_type=step_type,
            model=model,
            provider=provider,
            tool_name=tool_name,
            status=status,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=cost,
            safe_metadata=metadata,
        )
        self.db.add(step)
        execution.current_step = step_number
        execution.total_steps = step_number
        execution.total_tokens += input_tokens + output_tokens
        if cost is not None:
            execution.estimated_cost_usd = (execution.estimated_cost_usd or 0.0) + cost
        await self.db.flush()
        record_agent_step(step_type=step_type, status=status)
        return step

    async def _execute_tool(
        self,
        agent: Agent,
        execution: AgentExecution,
        tool_name: str,
        arguments: dict,
        *,
        step_number: int,
        user: User | None,
    ) -> dict:
        allowed = self._allowed_tools(agent)
        if tool_name not in allowed:
            raise ValueError(f"Tool {tool_name} is not authorized for this agent")
        tool = get_builtin(tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")

        cfg = agent.tool_configuration or {}
        require_approval_tools = set(cfg.get("require_approval_tools") or [])
        needs_approval = risk_requires_approval(tool.risk_level) or tool_name in require_approval_tools

        if needs_approval and execution.status != ExecutionStatus.WAITING_FOR_APPROVAL:
            approval = ApprovalRequest(
                organization_id=execution.organization_id,
                status=ApprovalStatus.PENDING,
                request_type="agent_tool",
                risk_level=tool.risk_level,
                fingerprint=f"agent:{execution.id}:{step_number}:{tool_name}",
                requester_id=execution.started_by,
                safe_snapshot={
                    "agent_id": str(agent.id),
                    "execution_id": str(execution.id),
                    "tool_name": tool_name,
                    "step_number": step_number,
                },
            )
            self.db.add(approval)
            await self.db.flush()
            execution.approval_id = approval.id
            await self.transition(execution, ExecutionStatus.WAITING_FOR_APPROVAL)
            await self.db.commit()
            return {"status": "waiting_for_approval", "approval_id": str(approval.id)}

        started = time.time()
        try:
            result = await execute_builtin(tool_name, arguments)
            status = "completed"
        except Exception as e:
            result = {"error": str(e)}
            status = "failed"
        latency = (time.time() - started) * 1000

        await self._record_step(
            execution,
            step_number=step_number,
            step_type="tool",
            tool_name=tool_name,
            latency_ms=latency,
            metadata={"result_status": status},
            status=status,
        )
        record_agent_tool_call(tool_name=tool_name, status=status)
        audit = AuditService(self.db)
        await audit.log(
            AUDIT_AGENT_TOOL_EXECUTED,
            "agent_execution",
            resource_id=str(execution.id),
            metadata={"tool": tool_name, "status": status, "duration_ms": round(latency, 2)},
            organization_id=execution.organization_id,
        )
        return result

    async def _call_model(
        self,
        agent: Agent,
        execution: AgentExecution,
        messages: list[ChatMessage],
        *,
        step_number: int,
        user: User | None,
        approval_id: str | None = None,
    ) -> tuple[str, list[dict] | None, dict]:
        model_cfg = agent.model_configuration or {}
        mode = model_cfg.get("execution_mode", "gateway")

        if mode == "direct":
            content = messages[-1].content if messages else ""
            return str(content or ""), None, {"provider": "direct", "model": "direct", "tokens": 0, "cost": None}

        payload = ChatCompletionRequest(
            model=model_cfg.get("model", "auto"),
            messages=messages,
            temperature=model_cfg.get("temperature"),
            max_tokens=model_cfg.get("max_tokens"),
            tools=self._tool_schemas(agent) or None,
            tool_choice=model_cfg.get("tool_choice", "auto"),
        )
        started = time.time()
        result = await execute_chat(payload, self.db, user, None, approval_id=approval_id)
        latency = (time.time() - started) * 1000
        choice = result.response.choices[0].message
        usage = result.response.usage
        tokens_in = usage.prompt_tokens if usage else 0
        tokens_out = usage.completion_tokens if usage else 0
        await self._record_step(
            execution,
            step_number=step_number,
            step_type="model",
            model=result.selected_model,
            provider=result.provider,
            latency_ms=latency,
            input_tokens=tokens_in,
            output_tokens=tokens_out,
            cost=result.estimated_total_cost,
        )
        meta = {
            "provider": result.provider,
            "model": result.selected_model,
            "tokens": tokens_in + tokens_out,
            "cost": result.estimated_total_cost,
        }
        return choice.content or "", choice.tool_calls, meta

    async def run(self, execution_id: uuid.UUID, *, user: User | None = None) -> AgentExecution:
        result = await self.db.execute(
            select(AgentExecution, Agent)
            .join(Agent, Agent.id == AgentExecution.agent_id)
            .where(AgentExecution.id == execution_id)
        )
        row = result.one_or_none()
        if not row:
            raise ValueError("Execution not found")
        execution, agent = row

        if agent.status != AgentStatus.ACTIVE:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = "Agent is not active"
            execution.error_code = "AGENT_INACTIVE"
            execution.completed_at = datetime.now(UTC)
            await self.db.commit()
            record_agent_execution(status=ExecutionStatus.FAILED)
            return execution

        if execution.status == ExecutionStatus.QUEUED:
            await self.transition(execution, ExecutionStatus.RUNNING)
            execution.started_at = datetime.now(UTC)
            audit = AuditService(self.db)
            await audit.log(
                AUDIT_AGENT_EXECUTION_STARTED,
                "agent_execution",
                resource_id=str(execution.id),
                metadata={"agent_id": str(agent.id)},
                organization_id=execution.organization_id,
            )

        started_at = execution.started_at.timestamp() if execution.started_at else time.time()
        memory = MemoryStore(self.db, execution.organization_id, agent.id)

        messages: list[ChatMessage] = [
            ChatMessage(role="system", content=agent.system_prompt or "You are a helpful assistant."),
        ]
        if execution.input_text:
            messages.append(ChatMessage(role="user", content=execution.input_text))

        final_output: str | None = None
        try:
            while True:
                execution = await self._refresh_execution(execution_id)
                if execution.status == ExecutionStatus.CANCELLED:
                    record_agent_execution(status=ExecutionStatus.CANCELLED)
                    await self.db.commit()
                    return execution
                if execution.status == ExecutionStatus.WAITING_FOR_APPROVAL:
                    await self.db.commit()
                    return execution

                await self._check_limits(agent, execution, started_at)
                step_number = execution.current_step + 1

                approval_id = str(execution.approval_id) if execution.approval_id else None
                content, tool_calls, _meta = await self._call_model(
                    agent,
                    execution,
                    messages,
                    step_number=step_number,
                    user=user,
                    approval_id=approval_id,
                )

                if tool_calls:
                    messages.append(ChatMessage(role="assistant", content=content, tool_calls=tool_calls))
                    for tc in tool_calls:
                        fn = tc.get("function") or {}
                        tool_name = fn.get("name", "")
                        raw_args = fn.get("arguments", "{}")
                        try:
                            arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                        except json.JSONDecodeError:
                            arguments = {}
                        tool_step = step_number + 1
                        await self._check_limits(agent, execution, started_at)
                        tool_result = await self._execute_tool(
                            agent,
                            execution,
                            tool_name,
                            arguments,
                            step_number=tool_step,
                            user=user,
                        )
                        if tool_result.get("status") == "waiting_for_approval":
                            record_agent_execution(status=ExecutionStatus.WAITING_FOR_APPROVAL)
                            return execution
                        messages.append(
                            ChatMessage(
                                role="tool",
                                tool_call_id=tc.get("id"),
                                content=json.dumps(tool_result, default=str),
                            )
                        )
                    continue

                final_output = content
                break

            execution.output_text = final_output
            await self.transition(execution, ExecutionStatus.COMPLETED)
            audit = AuditService(self.db)
            await audit.log(
                AUDIT_AGENT_EXECUTION_COMPLETED,
                "agent_execution",
                resource_id=str(execution.id),
                metadata={"steps": execution.total_steps},
                organization_id=execution.organization_id,
            )
            record_agent_execution(status=ExecutionStatus.COMPLETED)
            await self.db.commit()
            return execution

        except ExecutionLimitError as e:
            new_status = ExecutionStatus.TIMED_OUT if e.code == "TIMEOUT" else ExecutionStatus.FAILED
            if e.code == "MAX_STEPS":
                new_status = ExecutionStatus.COMPLETED
                execution.output_text = final_output or execution.output_text
            if can_transition(execution.status, new_status):
                await self.transition(execution, new_status, error_message=str(e), error_code=e.code)
            record_agent_execution(status=new_status)
            await self.db.commit()
            return execution
        except Exception as e:
            logger.exception("agent_execution_failed", execution_id=str(execution_id))
            if can_transition(execution.status, ExecutionStatus.FAILED):
                await self.transition(execution, ExecutionStatus.FAILED, error_message=str(e), error_code="EXECUTION_ERROR")
            record_agent_execution(status=ExecutionStatus.FAILED)
            await self.db.commit()
            return execution
