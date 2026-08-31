"""Workflow definition, scheduling, and execution APIs."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.org_context import OrgContext
from app.auth.rbac import Permission, require_permission
from app.db.base import get_db
from app.models.agent import (
    Workflow,
    WorkflowExecution,
    WorkflowNode,
    WorkflowSchedule,
    WorkflowStatus,
    WorkflowTrigger,
)
from app.schemas.agents import (
    CancelRequest,
    WorkflowCreate,
    WorkflowExecuteRequest,
    WorkflowExecutionResponse,
    WorkflowNodeInput,
    WorkflowResponse,
    WorkflowScheduleCreate,
    WorkflowTriggerCreate,
    WorkflowUpdate,
)
from app.services.agents.queue import enqueue_workflow_execution
from app.services.agents.tools import list_builtin_names
from app.services.agents.validation import validate_workflow
from app.services.agents.workflow_engine import (
    WORKFLOW_CANCELLED,
    WORKFLOW_COMPLETED,
    WORKFLOW_FAILED,
    WORKFLOW_QUEUED,
    WORKFLOW_RUNNING,
    WORKFLOW_WAITING,
    WorkflowExecutionEngine,
)

router = APIRouter(prefix="/workflows", tags=["Workflows"])

_VALID_WORKFLOW_STATUS = {s.value for s in WorkflowStatus}
_CANCELLABLE = {WORKFLOW_QUEUED, WORKFLOW_RUNNING, WORKFLOW_WAITING}


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def _workflow_response(workflow: Workflow, nodes: list[WorkflowNode] | None = None) -> WorkflowResponse:
    node_list = nodes if nodes is not None else (workflow.nodes or [])
    return WorkflowResponse(
        id=workflow.id,
        organization_id=workflow.organization_id,
        name=workflow.name,
        description=workflow.description,
        status=workflow.status,
        definition=workflow.definition or {},
        created_by=workflow.created_by,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
        nodes=[
            WorkflowNodeInput(
                node_key=n.node_key,
                node_type=n.node_type,
                config=n.config or {},
                next_on_success=n.next_on_success,
                next_on_failure=n.next_on_failure,
                next_on_true=n.next_on_true,
                next_on_false=n.next_on_false,
            )
            for n in node_list
        ],
    )


async def _get_workflow(db: AsyncSession, org_id: uuid.UUID, workflow_id: uuid.UUID) -> Workflow:
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id, Workflow.organization_id == org_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


async def _sync_nodes(db: AsyncSession, workflow: Workflow, nodes: list[WorkflowNodeInput]) -> None:
    existing = await db.execute(select(WorkflowNode).where(WorkflowNode.workflow_id == workflow.id))
    for row in existing.scalars().all():
        await db.delete(row)
    for node in nodes:
        db.add(
            WorkflowNode(
                workflow_id=workflow.id,
                node_key=node.node_key,
                node_type=node.node_type,
                config=node.config,
                next_on_success=node.next_on_success,
                next_on_failure=node.next_on_failure,
                next_on_true=node.next_on_true,
                next_on_false=node.next_on_false,
            )
        )


@router.get("", response_model=list[WorkflowResponse])
async def list_workflows(
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Workflow)
        .where(Workflow.organization_id == ctx.organization_id)
        .order_by(Workflow.name)
    )
    return [_workflow_response(w) for w in result.scalars().all()]


@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    payload: WorkflowCreate,
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    if payload.nodes:
        validation = validate_workflow(
            [n.model_dump() for n in payload.nodes],
            allowed_tools=set(list_builtin_names()),
        )
        if not validation.valid:
            raise HTTPException(status_code=400, detail={"errors": validation.errors})
    workflow = Workflow(
        organization_id=ctx.organization_id,
        name=payload.name,
        description=payload.description,
        definition=payload.definition,
        status=WorkflowStatus.DRAFT,
        created_by=ctx.user.id,
    )
    db.add(workflow)
    await db.flush()
    if payload.nodes:
        await _sync_nodes(db, workflow, payload.nodes)
    await db.commit()
    await db.refresh(workflow)
    return _workflow_response(workflow)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_READ)),
    db: AsyncSession = Depends(get_db),
):
    workflow = await _get_workflow(db, ctx.organization_id, workflow_id)
    return _workflow_response(workflow)


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: uuid.UUID,
    payload: WorkflowUpdate,
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    workflow = await _get_workflow(db, ctx.organization_id, workflow_id)
    data = payload.model_dump(exclude_unset=True)
    nodes = data.pop("nodes", None)
    if "status" in data and data["status"] not in _VALID_WORKFLOW_STATUS:
        raise HTTPException(status_code=400, detail=f"Invalid status: {data['status']}")
    for key, value in data.items():
        setattr(workflow, key, value)
    if nodes is not None:
        node_inputs = [WorkflowNodeInput(**n) if isinstance(n, dict) else n for n in nodes]
        validation = validate_workflow(
            [n.model_dump() for n in node_inputs],
            allowed_tools=set(list_builtin_names()),
        )
        if workflow.status == WorkflowStatus.ACTIVE and not validation.valid:
            raise HTTPException(status_code=400, detail={"errors": validation.errors})
        await _sync_nodes(db, workflow, node_inputs)
    workflow.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(workflow)
    return _workflow_response(workflow)


@router.post("/{workflow_id}/activate", response_model=WorkflowResponse)
async def activate_workflow(
    workflow_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    workflow = await _get_workflow(db, ctx.organization_id, workflow_id)
    nodes = workflow.nodes or []
    validation = validate_workflow(
        [
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
        ],
        allowed_tools=set(list_builtin_names()),
    )
    if not validation.valid:
        raise HTTPException(status_code=400, detail={"errors": validation.errors})
    workflow.status = WorkflowStatus.ACTIVE
    await db.commit()
    await db.refresh(workflow)
    return _workflow_response(workflow)


@router.post("/{workflow_id}/disable", response_model=WorkflowResponse)
async def disable_workflow(
    workflow_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    workflow = await _get_workflow(db, ctx.organization_id, workflow_id)
    workflow.status = WorkflowStatus.DISABLED
    await db.commit()
    await db.refresh(workflow)
    return _workflow_response(workflow)


@router.post("/{workflow_id}/execute", response_model=WorkflowExecutionResponse, status_code=202)
async def execute_workflow(
    workflow_id: uuid.UUID,
    payload: WorkflowExecuteRequest,
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_EXECUTE)),
    db: AsyncSession = Depends(get_db),
):
    workflow = await _get_workflow(db, ctx.organization_id, workflow_id)
    if workflow.status != WorkflowStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Workflow must be active to execute")

    if payload.idempotency_key:
        existing = await db.execute(
            select(WorkflowExecution).where(
                WorkflowExecution.organization_id == ctx.organization_id,
                WorkflowExecution.idempotency_key == payload.idempotency_key,
            )
        )
        found = existing.scalar_one_or_none()
        if found:
            return WorkflowExecutionResponse.model_validate(found)

    execution = WorkflowExecution(
        organization_id=ctx.organization_id,
        workflow_id=workflow.id,
        status=WORKFLOW_QUEUED,
        context=payload.context,
        idempotency_key=payload.idempotency_key,
        started_by=ctx.user.id,
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    if payload.sync:
        engine = WorkflowExecutionEngine(db)
        execution = await engine.run(execution.id)
        return WorkflowExecutionResponse.model_validate(execution)

    enqueued = await enqueue_workflow_execution(str(execution.id))
    if not enqueued:
        engine = WorkflowExecutionEngine(db)
        execution = await engine.run(execution.id)
    return WorkflowExecutionResponse.model_validate(execution)


@router.get("/executions/list", response_model=list[WorkflowExecutionResponse])
async def list_workflow_executions(
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_READ)),
    db: AsyncSession = Depends(get_db),
    workflow_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, le=200),
):
    q = select(WorkflowExecution).where(WorkflowExecution.organization_id == ctx.organization_id)
    if workflow_id:
        q = q.where(WorkflowExecution.workflow_id == workflow_id)
    q = q.order_by(WorkflowExecution.created_at.desc()).limit(limit)
    result = await db.execute(q)
    return [WorkflowExecutionResponse.model_validate(e) for e in result.scalars().all()]


@router.get("/executions/{execution_id}", response_model=WorkflowExecutionResponse)
async def get_workflow_execution(
    execution_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkflowExecution).where(
            WorkflowExecution.id == execution_id,
            WorkflowExecution.organization_id == ctx.organization_id,
        )
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Workflow execution not found")
    return WorkflowExecutionResponse.model_validate(execution)


@router.post("/executions/{execution_id}/cancel", response_model=WorkflowExecutionResponse)
async def cancel_workflow_execution(
    execution_id: uuid.UUID,
    payload: CancelRequest,
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_EXECUTE)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkflowExecution).where(
            WorkflowExecution.id == execution_id,
            WorkflowExecution.organization_id == ctx.organization_id,
        )
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Workflow execution not found")
    if execution.status not in _CANCELLABLE:
        raise HTTPException(status_code=400, detail=f"Cannot cancel workflow in status {execution.status}")
    execution.status = WORKFLOW_CANCELLED
    execution.error_message = payload.reason or "Cancelled by user"
    execution.completed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(execution)
    return WorkflowExecutionResponse.model_validate(execution)


@router.post("/{workflow_id}/schedules", status_code=201)
async def create_schedule(
    workflow_id: uuid.UUID,
    payload: WorkflowScheduleCreate,
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    await _get_workflow(db, ctx.organization_id, workflow_id)
    schedule = WorkflowSchedule(
        organization_id=ctx.organization_id,
        workflow_id=workflow_id,
        schedule_type=payload.schedule_type,
        cron_expression=payload.cron_expression,
        run_at=payload.run_at,
        is_enabled=payload.is_enabled,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return {"id": str(schedule.id), "workflow_id": str(workflow_id)}


@router.post("/{workflow_id}/triggers", status_code=201)
async def create_trigger(
    workflow_id: uuid.UUID,
    payload: WorkflowTriggerCreate,
    ctx: OrgContext = Depends(require_permission(Permission.AGENTS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    await _get_workflow(db, ctx.organization_id, workflow_id)
    secret = payload.secret or secrets.token_urlsafe(32)
    trigger = WorkflowTrigger(
        organization_id=ctx.organization_id,
        workflow_id=workflow_id,
        trigger_type=payload.trigger_type,
        secret_hash=_hash_secret(secret),
    )
    db.add(trigger)
    await db.commit()
    await db.refresh(trigger)
    return {"id": str(trigger.id), "workflow_id": str(workflow_id), "secret": secret}


@router.post("/triggers/{trigger_id}/webhook", status_code=202)
async def webhook_trigger(
    trigger_id: uuid.UUID,
    request: Request,
    authorization: str | None = Header(None),
    x_modelbridge_signature: str | None = Header(None),
    x_modelbridge_timestamp: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(WorkflowTrigger).where(WorkflowTrigger.id == trigger_id))
    trigger = result.scalar_one_or_none()
    if not trigger or not trigger.is_enabled:
        raise HTTPException(status_code=404, detail="Trigger not found")

    body = await request.body()
    if trigger.secret_hash:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token")
        token = authorization[7:]
        if _hash_secret(token) != trigger.secret_hash:
            raise HTTPException(status_code=401, detail="Invalid webhook token")
        if x_modelbridge_signature and x_modelbridge_timestamp:
            try:
                ts = int(x_modelbridge_timestamp)
            except ValueError as e:
                raise HTTPException(status_code=401, detail="Invalid timestamp") from e
            if abs(datetime.now(UTC).timestamp() - ts) > 300:
                raise HTTPException(status_code=401, detail="Webhook timestamp expired")
            expected = hmac.new(
                token.encode(),
                f"{x_modelbridge_timestamp}.{body.decode()}".encode(),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, x_modelbridge_signature):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")

    import json

    try:
        event = json.loads(body)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from e

    execution = WorkflowExecution(
        organization_id=trigger.organization_id,
        workflow_id=trigger.workflow_id,
        status=WORKFLOW_QUEUED,
        context={"webhook_event": event},
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)
    await enqueue_workflow_execution(str(execution.id))
    return {"execution_id": str(execution.id), "status": WORKFLOW_QUEUED}
