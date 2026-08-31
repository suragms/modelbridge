"""Agent definition and execution APIs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.org_context import OrgContext
from app.auth.rbac import Permission, require_permission
from app.db.base import get_db
from app.models.agent import Agent, AgentExecution, AgentStatus, AgentStep, ExecutionStatus
from app.models.user import User
from app.schemas.agents import (
    AgentCreate,
    AgentExecuteRequest,
    AgentExecutionResponse,
    AgentOverviewResponse,
    AgentResponse,
    AgentStepResponse,
    AgentUpdate,
    CancelRequest,
)
from app.services.agents.engine import AgentExecutionEngine
from app.services.agents.queue import enqueue_agent_execution
from app.services.agents.state import can_transition
from app.services.agents.tools import list_builtin_names
from app.services.audit import AuditService

router = APIRouter(prefix="/agents", tags=["Agents"])

_VALID_AGENT_STATUS = {s.value for s in AgentStatus}
_CANCELLABLE = {
    ExecutionStatus.QUEUED,
    ExecutionStatus.RUNNING,
    ExecutionStatus.WAITING_FOR_APPROVAL,
}


def _execution_response(execution: AgentExecution) -> AgentExecutionResponse:
    steps = [
        AgentStepResponse(
            id=s.id,
            step_number=s.step_number,
            step_type=s.step_type,
            model=s.model,
            provider=s.provider,
            tool_name=s.tool_name,
            status=s.status,
            latency_ms=s.latency_ms,
            input_tokens=s.input_tokens,
            output_tokens=s.output_tokens,
            estimated_cost_usd=s.estimated_cost_usd,
            safe_metadata=s.safe_metadata,
            created_at=s.created_at,
        )
        for s in (execution.steps or [])
    ]
    return AgentExecutionResponse(
        id=execution.id,
        organization_id=execution.organization_id,
        agent_id=execution.agent_id,
        status=execution.status,
        input_text=execution.input_text,
        output_text=execution.output_text,
        session_id=execution.session_id,
        current_step=execution.current_step,
        total_steps=execution.total_steps,
        total_tokens=execution.total_tokens,
        estimated_cost_usd=execution.estimated_cost_usd,
        error_message=execution.error_message,
        error_code=execution.error_code,
        approval_id=execution.approval_id,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        created_at=execution.created_at,
        steps=steps,
    )


async def _get_agent(db: AsyncSession, org_id: uuid.UUID, agent_id: uuid.UUID) -> Agent:
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.organization_id == org_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


async def _get_execution(db: AsyncSession, org_id: uuid.UUID, execution_id: uuid.UUID) -> AgentExecution:
    result = await db.execute(
        select(AgentExecution).where(
            AgentExecution.id == execution_id,
            AgentExecution.organization_id == org_id,
        )
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


@router.get("/overview", response_model=AgentOverviewResponse)
async def agents_overview(
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_READ)),
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(
        select(func.count()).select_from(Agent).where(Agent.organization_id == ctx.organization_id)
    )
    active = await db.scalar(
        select(func.count())
        .select_from(Agent)
        .where(Agent.organization_id == ctx.organization_id, Agent.status == AgentStatus.ACTIVE)
    )
    since = datetime.now(UTC) - timedelta(days=7)
    recent = await db.scalar(
        select(func.count())
        .select_from(AgentExecution)
        .where(AgentExecution.organization_id == ctx.organization_id, AgentExecution.created_at >= since)
    )
    completed = await db.scalar(
        select(func.count())
        .select_from(AgentExecution)
        .where(
            AgentExecution.organization_id == ctx.organization_id,
            AgentExecution.status == ExecutionStatus.COMPLETED,
            AgentExecution.created_at >= since,
        )
    )
    failures = await db.scalar(
        select(func.count())
        .select_from(AgentExecution)
        .where(
            AgentExecution.organization_id == ctx.organization_id,
            AgentExecution.status == ExecutionStatus.FAILED,
            AgentExecution.created_at >= since,
        )
    )
    finished = (completed or 0) + (failures or 0)
    success_rate = (completed or 0) / finished if finished else 0.0
    avg_duration = await db.scalar(
        select(
            func.avg(
                func.extract("epoch", AgentExecution.completed_at)
                - func.extract("epoch", AgentExecution.started_at)
            )
        ).where(
            AgentExecution.organization_id == ctx.organization_id,
            AgentExecution.completed_at.isnot(None),
            AgentExecution.started_at.isnot(None),
            AgentExecution.created_at >= since,
        )
    )
    total_cost = await db.scalar(
        select(func.sum(AgentExecution.estimated_cost_usd)).where(
            AgentExecution.organization_id == ctx.organization_id,
            AgentExecution.created_at >= since,
        )
    )
    return AgentOverviewResponse(
        total_agents=total or 0,
        active_agents=active or 0,
        recent_executions=recent or 0,
        success_rate=round(success_rate, 4),
        failures=failures or 0,
        average_duration_ms=float(avg_duration or 0) * 1000 if avg_duration else None,
        estimated_cost_usd=float(total_cost) if total_cost else None,
    )


@router.get("/tools/builtin")
async def list_tools(
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_READ)),
):
    del ctx
    return {"tools": list_builtin_names()}


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_READ)),
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None),
):
    q = select(Agent).where(Agent.organization_id == ctx.organization_id)
    if status:
        q = q.where(Agent.status == status)
    q = q.order_by(Agent.name)
    result = await db.execute(q)
    return [AgentResponse.model_validate(a) for a in result.scalars().all()]


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    payload: AgentCreate,
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    if payload.status not in _VALID_AGENT_STATUS:
        raise HTTPException(status_code=400, detail=f"Invalid status: {payload.status}")
    agent = Agent(
        organization_id=ctx.organization_id,
        name=payload.name,
        description=payload.description,
        status=payload.status,
        system_prompt=payload.system_prompt,
        model_configuration=payload.model_configuration,
        tool_configuration=payload.tool_configuration,
        memory_configuration=payload.memory_configuration,
        max_steps=min(payload.max_steps, 100),
        timeout_seconds=min(payload.timeout_seconds, 3600),
        max_tokens=payload.max_tokens,
        max_budget_usd=payload.max_budget_usd,
        created_by=ctx.user.id,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return AgentResponse.model_validate(agent)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_READ)),
    db: AsyncSession = Depends(get_db),
):
    agent = await _get_agent(db, ctx.organization_id, agent_id)
    return AgentResponse.model_validate(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: uuid.UUID,
    payload: AgentUpdate,
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    agent = await _get_agent(db, ctx.organization_id, agent_id)
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in _VALID_AGENT_STATUS:
        raise HTTPException(status_code=400, detail=f"Invalid status: {data['status']}")
    if "max_steps" in data:
        data["max_steps"] = min(data["max_steps"], 100)
    if "timeout_seconds" in data:
        data["timeout_seconds"] = min(data["timeout_seconds"], 3600)
    for key, value in data.items():
        setattr(agent, key, value)
    agent.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(agent)
    return AgentResponse.model_validate(agent)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    agent = await _get_agent(db, ctx.organization_id, agent_id)
    agent.status = AgentStatus.ARCHIVED
    await db.commit()


@router.post("/{agent_id}/execute", response_model=AgentExecutionResponse, status_code=202)
async def execute_agent(
    agent_id: uuid.UUID,
    payload: AgentExecuteRequest,
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_EXECUTE)),
    db: AsyncSession = Depends(get_db),
):
    agent = await _get_agent(db, ctx.organization_id, agent_id)
    if agent.status != AgentStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Agent must be active to execute")

    if payload.idempotency_key:
        existing = await db.execute(
            select(AgentExecution).where(
                AgentExecution.organization_id == ctx.organization_id,
                AgentExecution.idempotency_key == payload.idempotency_key,
            )
        )
        found = existing.scalar_one_or_none()
        if found:
            return _execution_response(found)

    execution = AgentExecution(
        organization_id=ctx.organization_id,
        agent_id=agent.id,
        status=ExecutionStatus.QUEUED,
        input_text=payload.input_text,
        session_id=payload.session_id,
        idempotency_key=payload.idempotency_key,
        started_by=ctx.user.id,
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    if payload.sync:
        user = ctx.user
        engine = AgentExecutionEngine(db)
        execution = await engine.run(execution.id, user=user)
        await db.refresh(execution)
        return _execution_response(execution)

    enqueued = await enqueue_agent_execution(str(execution.id))
    if not enqueued:
        user = ctx.user
        engine = AgentExecutionEngine(db)
        execution = await engine.run(execution.id, user=user)
        await db.refresh(execution)
    return _execution_response(execution)


@router.get("/executions/list", response_model=list[AgentExecutionResponse])
async def list_executions(
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_READ)),
    db: AsyncSession = Depends(get_db),
    agent_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, le=200),
):
    q = select(AgentExecution).where(AgentExecution.organization_id == ctx.organization_id)
    if agent_id:
        q = q.where(AgentExecution.agent_id == agent_id)
    q = q.order_by(AgentExecution.created_at.desc()).limit(limit)
    result = await db.execute(q)
    return [_execution_response(e) for e in result.scalars().all()]


@router.get("/executions/{execution_id}", response_model=AgentExecutionResponse)
async def get_execution(
    execution_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_READ)),
    db: AsyncSession = Depends(get_db),
):
    execution = await _get_execution(db, ctx.organization_id, execution_id)
    return _execution_response(execution)


@router.post("/executions/{execution_id}/cancel", response_model=AgentExecutionResponse)
async def cancel_execution(
    execution_id: uuid.UUID,
    payload: CancelRequest,
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_EXECUTE)),
    db: AsyncSession = Depends(get_db),
):
    execution = await _get_execution(db, ctx.organization_id, execution_id)
    if execution.status not in _CANCELLABLE:
        raise HTTPException(status_code=400, detail=f"Cannot cancel execution in status {execution.status}")
    if not can_transition(execution.status, ExecutionStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="Invalid cancellation transition")
    execution.status = ExecutionStatus.CANCELLED
    execution.cancelled_by = ctx.user.id
    execution.cancel_reason = payload.reason
    execution.completed_at = datetime.now(UTC)
    audit = AuditService(db)
    await audit.log(
        "agent.execution_cancelled",
        "agent_execution",
        resource_id=str(execution.id),
        organization_id=ctx.organization_id,
    )
    await db.commit()
    await db.refresh(execution)
    return _execution_response(execution)
