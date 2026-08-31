"""Deterministic workflow execution engine."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import (
    Agent,
    AgentMessage,
    AgentStatus,
    Workflow,
    WorkflowExecution,
    WorkflowNode,
    WorkflowStatus,
)
from app.services.agents.engine import AgentExecutionEngine
from app.services.agents.tools import execute_builtin, list_builtin_names
from app.services.agents.validation import validate_workflow
from app.services.metrics import record_workflow_execution

logger = structlog.get_logger()

WORKFLOW_QUEUED = "queued"
WORKFLOW_RUNNING = "running"
WORKFLOW_WAITING = "waiting"
WORKFLOW_COMPLETED = "completed"
WORKFLOW_FAILED = "failed"
WORKFLOW_CANCELLED = "cancelled"


class WorkflowExecutionEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(self, execution_id: uuid.UUID) -> WorkflowExecution:
        result = await self.db.execute(
            select(WorkflowExecution, Workflow)
            .join(Workflow, Workflow.id == WorkflowExecution.workflow_id)
            .where(WorkflowExecution.id == execution_id)
        )
        row = result.one_or_none()
        if not row:
            raise ValueError("Workflow execution not found")
        execution, workflow = row

        if workflow.status != WorkflowStatus.ACTIVE:
            execution.status = WORKFLOW_FAILED
            execution.error_message = "Workflow is not active"
            execution.completed_at = datetime.now(UTC)
            await self.db.commit()
            record_workflow_execution(status=WORKFLOW_FAILED)
            return execution

        nodes_result = await self.db.execute(
            select(WorkflowNode).where(WorkflowNode.workflow_id == workflow.id)
        )
        nodes = nodes_result.scalars().all()
        node_dicts = [
            {
                "node_key": n.node_key,
                "node_type": n.node_type,
                "config": n.config or {},
                "next_on_success": n.next_on_success,
                "next_on_failure": n.next_on_failure,
                "next_on_true": n.next_on_true,
                "next_on_false": n.next_on_false,
            }
            for n in nodes
        ]
        validation = validate_workflow(node_dicts, allowed_tools=set(list_builtin_names()))
        if not validation.valid:
            execution.status = WORKFLOW_FAILED
            execution.error_message = "; ".join(validation.errors)
            execution.completed_at = datetime.now(UTC)
            await self.db.commit()
            record_workflow_execution(status=WORKFLOW_FAILED)
            return execution

        by_key = {n.node_key: n for n in nodes}
        start = next(n for n in nodes if n.node_type == "start")
        current_key = execution.current_node_key or start.node_key
        execution.status = WORKFLOW_RUNNING
        execution.started_at = execution.started_at or datetime.now(UTC)
        ctx = dict(execution.context or {})
        visits = 0

        try:
            while current_key:
                visits += 1
                if visits > 100:
                    raise RuntimeError("Workflow exceeded maximum node visits")
                node = by_key.get(current_key)
                if not node:
                    raise RuntimeError(f"Unknown node {current_key}")

                execution.current_node_key = current_key
                await self.db.flush()

                if node.node_type == "terminal":
                    execution.status = WORKFLOW_COMPLETED
                    execution.completed_at = datetime.now(UTC)
                    ctx["result"] = node.config.get("result", ctx.get("last_output"))
                    execution.context = ctx
                    record_workflow_execution(status=WORKFLOW_COMPLETED)
                    await self.db.commit()
                    return execution

                if node.node_type == "delay":
                    current_key = node.next_on_success
                    continue

                if node.node_type == "condition":
                    expr = (node.config or {}).get("field")
                    expected = (node.config or {}).get("equals")
                    actual = ctx.get(expr) if expr else None
                    current_key = node.next_on_true if actual == expected else node.next_on_false
                    continue

                if node.node_type == "tool":
                    tool_name = (node.config or {}).get("tool_name")
                    args = (node.config or {}).get("arguments") or {}
                    result = await execute_builtin(tool_name, args)
                    ctx["last_tool_result"] = result
                    ctx["last_output"] = str(result)
                    current_key = node.next_on_success if "error" not in result else node.next_on_failure
                    continue

                if node.node_type == "agent":
                    agent_id = (node.config or {}).get("agent_id")
                    if not agent_id:
                        raise RuntimeError(f"Agent node {node.node_key} missing agent_id")
                    agent_result = await self.db.execute(
                        select(Agent).where(
                            Agent.id == uuid.UUID(str(agent_id)),
                            Agent.organization_id == execution.organization_id,
                        )
                    )
                    agent = agent_result.scalar_one_or_none()
                    if not agent or agent.status != AgentStatus.ACTIVE:
                        current_key = node.next_on_failure
                        continue
                    from app.models.agent import AgentExecution, ExecutionStatus

                    child = AgentExecution(
                        organization_id=execution.organization_id,
                        agent_id=agent.id,
                        status=ExecutionStatus.QUEUED,
                        input_text=ctx.get("input_text") or ctx.get("last_output"),
                        session_id=ctx.get("session_id"),
                        started_by=execution.started_by,
                    )
                    self.db.add(child)
                    await self.db.flush()
                    engine = AgentExecutionEngine(self.db)
                    child_exec = await engine.run(child.id)
                    ctx["last_agent_execution_id"] = str(child_exec.id)
                    ctx["last_output"] = child_exec.output_text
                    if child_exec.estimated_cost_usd:
                        execution.estimated_cost_usd = (execution.estimated_cost_usd or 0) + child_exec.estimated_cost_usd
                    self.db.add(
                        AgentMessage(
                            organization_id=execution.organization_id,
                            source_agent_id=agent.id,
                            workflow_execution_id=execution.id,
                            message_type="agent_result",
                            payload={"execution_id": str(child_exec.id), "status": child_exec.status},
                        )
                    )
                    current_key = (
                        node.next_on_success
                        if child_exec.status == ExecutionStatus.COMPLETED
                        else node.next_on_failure
                    )
                    continue

                if node.node_type == "approval":
                    execution.status = WORKFLOW_WAITING
                    ctx["waiting_node"] = node.node_key
                    execution.context = ctx
                    record_workflow_execution(status=WORKFLOW_WAITING)
                    await self.db.commit()
                    return execution

                current_key = node.next_on_success

            execution.status = WORKFLOW_FAILED
            execution.error_message = "Workflow ended without reaching terminal"
            execution.completed_at = datetime.now(UTC)
            record_workflow_execution(status=WORKFLOW_FAILED)
            await self.db.commit()
            return execution
        except Exception as e:
            logger.exception("workflow_execution_failed", execution_id=str(execution_id))
            execution.status = WORKFLOW_FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now(UTC)
            record_workflow_execution(status=WORKFLOW_FAILED)
            await self.db.commit()
            return execution
