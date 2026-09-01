"""AI Studio APIs."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.org_context import OrgContext
from app.auth.rbac import Permission, require_permission
from app.db.base import get_db
from app.models.agent import Agent, Workflow, WorkflowNode, WorkflowStatus
from app.models.studio import (
    EvaluationDataset,
    EvaluationSuite,
    PromptTemplate,
    PromptVersion,
    STUDIO_NODE_TYPES,
    StudioAgentVersion,
    StudioComment,
    StudioDeployment,
    StudioDeploymentStatus,
    StudioVersionHistory,
    StudioVersionStatus,
    StudioWorkflowVersion,
)
from app.schemas.agents import WorkflowNodeInput
from app.schemas.chat import ChatCompletionRequest, ChatMessage
from app.schemas.studio import (
    DatasetCreate,
    DatasetResponse,
    EvaluationResultResponse,
    EvaluationRunResponse,
    EvaluationSuiteCreate,
    ImportRequest,
    PromptCreate,
    PromptResponse,
    PromptTestRequest,
    PromptVersionCreate,
    PromptVersionResponse,
    StudioAgentConfigUpdate,
    StudioCommentCreate,
    StudioCompareRequest,
    StudioDeploymentCreate,
    StudioOverviewResponse,
    StudioWorkflowCreate,
    StudioWorkflowUpdate,
    StudioWorkflowVersionResponse,
)
from app.services.agents.tools import list_builtin_names
from app.services.gateway import execute_chat
from app.services.metrics import record_studio_deployment, record_studio_workflow
from app.services.studio.deployments import DeploymentService
from app.services.studio.evaluations import EvaluationService
from app.services.studio.import_export import export_resource, validate_import
from app.services.studio.prompts import PromptService
from app.services.studio.workflows import compile_visual_to_engine, validate_visual_workflow

router = APIRouter(prefix="/studio", tags=["AI Studio"])
prompts_router = APIRouter(prefix="/prompts", tags=["Prompts"])
evaluations_router = APIRouter(prefix="/evaluations", tags=["Evaluations"])
evaluation_runs_router = APIRouter(prefix="/evaluation-runs", tags=["Evaluation Runs"])

STUDIO_NODE_CATALOG = [
    {
        "type": "trigger",
        "label": "Trigger",
        "inputs": [],
        "outputs": [{"id": "default", "label": "Next"}],
        "config_schema": {"type": "object", "properties": {"trigger_type": {"type": "string"}}},
    },
    {
        "type": "ai_model",
        "label": "AI Model",
        "inputs": [{"id": "default", "label": "In"}],
        "outputs": [{"id": "default", "label": "Out"}, {"id": "failure", "label": "Failure"}],
        "config_schema": {"type": "object", "required": ["model"], "properties": {"model": {"type": "string"}}},
    },
    {
        "type": "agent",
        "label": "Agent",
        "inputs": [{"id": "default", "label": "In"}],
        "outputs": [{"id": "default", "label": "Out"}, {"id": "failure", "label": "Failure"}],
        "config_schema": {"type": "object", "required": ["agent_id"], "properties": {"agent_id": {"type": "string"}}},
    },
    {
        "type": "condition",
        "label": "Condition",
        "inputs": [{"id": "default", "label": "In"}],
        "outputs": [{"id": "true", "label": "True"}, {"id": "false", "label": "False"}],
        "config_schema": {"type": "object", "required": ["field"], "properties": {"field": {"type": "string"}}},
    },
    {
        "type": "transform",
        "label": "Transform",
        "inputs": [{"id": "default", "label": "In"}],
        "outputs": [{"id": "default", "label": "Out"}],
        "config_schema": {"type": "object"},
    },
    {
        "type": "integration",
        "label": "Integration",
        "inputs": [{"id": "default", "label": "In"}],
        "outputs": [{"id": "default", "label": "Out"}],
        "config_schema": {"type": "object", "properties": {"integration_id": {"type": "string"}}},
    },
    {
        "type": "webhook",
        "label": "Webhook",
        "inputs": [],
        "outputs": [{"id": "default", "label": "Next"}],
        "config_schema": {"type": "object"},
    },
    {
        "type": "approval",
        "label": "Approval",
        "inputs": [{"id": "default", "label": "In"}],
        "outputs": [{"id": "default", "label": "Approved"}, {"id": "failure", "label": "Rejected"}],
        "config_schema": {"type": "object"},
    },
    {
        "type": "output",
        "label": "Output",
        "inputs": [{"id": "default", "label": "In"}],
        "outputs": [],
        "config_schema": {"type": "object"},
    },
]


@router.get("/nodes")
async def studio_node_catalog(
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_READ)),
):
    return {"node_types": sorted(STUDIO_NODE_TYPES), "catalog": STUDIO_NODE_CATALOG}


@router.get("/overview", response_model=StudioOverviewResponse)
async def studio_overview(
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_READ)),
    db: AsyncSession = Depends(get_db),
):
    wf = await db.execute(select(func.count()).select_from(Workflow).where(Workflow.organization_id == ctx.organization_id))
    ag = await db.execute(select(func.count()).select_from(Agent).where(Agent.organization_id == ctx.organization_id))
    pr = await db.execute(select(func.count()).select_from(PromptTemplate).where(PromptTemplate.organization_id == ctx.organization_id))
    ev = await db.execute(select(func.count()).select_from(EvaluationSuite).where(EvaluationSuite.organization_id == ctx.organization_id))
    dep = await db.execute(select(func.count()).select_from(StudioDeployment).where(StudioDeployment.organization_id == ctx.organization_id))
    hist = await db.execute(
        select(StudioVersionHistory)
        .where(StudioVersionHistory.organization_id == ctx.organization_id)
        .order_by(StudioVersionHistory.created_at.desc())
        .limit(10)
    )
    return StudioOverviewResponse(
        workflows=wf.scalar() or 0,
        agents=ag.scalar() or 0,
        prompts=pr.scalar() or 0,
        evaluations=ev.scalar() or 0,
        deployments=dep.scalar() or 0,
        recent_activity=[
            {
                "resource_type": h.resource_type,
                "resource_id": str(h.resource_id),
                "version": h.version,
                "summary": h.change_summary,
                "timestamp": h.created_at.isoformat(),
            }
            for h in hist.scalars().all()
        ],
    )


async def _sync_workflow_nodes(db: AsyncSession, workflow: Workflow, nodes: list[dict]) -> None:
    existing = await db.execute(select(WorkflowNode).where(WorkflowNode.workflow_id == workflow.id))
    for row in existing.scalars().all():
        await db.delete(row)
    await db.flush()
    for n in nodes:
        db.add(
            WorkflowNode(
                workflow_id=workflow.id,
                node_key=n["node_key"],
                node_type=n["node_type"],
                config=n.get("config") or {},
                next_on_success=n.get("next_on_success"),
                next_on_failure=n.get("next_on_failure"),
                next_on_true=n.get("next_on_true"),
                next_on_false=n.get("next_on_false"),
            )
        )
    await db.flush()


@router.get("/workflows")
async def list_studio_workflows(
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Workflow).where(Workflow.organization_id == ctx.organization_id).order_by(Workflow.updated_at.desc())
    )
    return [
        {
            "id": str(w.id),
            "name": w.name,
            "status": w.status,
            "description": w.description,
            "updated_at": w.updated_at.isoformat(),
        }
        for w in result.scalars().all()
    ]


@router.post("/workflows", status_code=status.HTTP_201_CREATED)
async def create_studio_workflow(
    payload: StudioWorkflowCreate,
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    validation = validate_visual_workflow(payload.visual_definition)
    if not validation.valid:
        raise HTTPException(status_code=400, detail={"errors": validation.errors, "warnings": validation.warnings})

    workflow = Workflow(
        organization_id=ctx.organization_id,
        name=payload.name,
        description=payload.description,
        status=WorkflowStatus.DRAFT,
        definition={"studio": True, "visual": payload.visual_definition},
        created_by=ctx.user.id,
    )
    db.add(workflow)
    await db.flush()

    version = StudioWorkflowVersion(
        workflow_id=workflow.id,
        organization_id=ctx.organization_id,
        version=1,
        status=StudioVersionStatus.DRAFT,
        visual_definition=payload.visual_definition,
        change_summary="Initial draft",
        created_by=ctx.user.id,
    )
    db.add(version)
    db.add(
        StudioVersionHistory(
            organization_id=ctx.organization_id,
            resource_type="workflow",
            resource_id=workflow.id,
            version=1,
            actor_id=ctx.user.id,
            change_summary="Created",
        )
    )
    record_studio_workflow(status="created")
    await db.commit()
    return {"workflow_id": str(workflow.id), "version_id": str(version.id)}


@router.get("/workflows/{workflow_id}")
async def get_studio_workflow(
    workflow_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_READ)),
    db: AsyncSession = Depends(get_db),
):
    wf = await db.get(Workflow, workflow_id)
    if not wf or wf.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    versions = await db.execute(
        select(StudioWorkflowVersion)
        .where(StudioWorkflowVersion.workflow_id == workflow_id)
        .order_by(StudioWorkflowVersion.version.desc())
    )
    latest = versions.scalars().first()
    return {
        "id": str(wf.id),
        "name": wf.name,
        "status": wf.status,
        "visual_definition": (latest.visual_definition if latest else {}),
        "versions": [
            StudioWorkflowVersionResponse(
                id=v.id,
                workflow_id=v.workflow_id,
                version=v.version,
                status=v.status,
                visual_definition=v.visual_definition or {},
                change_summary=v.change_summary,
                created_at=v.created_at,
            ).model_dump()
            for v in versions.scalars().all()
        ],
    }


@router.patch("/workflows/{workflow_id}")
async def update_studio_workflow(
    workflow_id: uuid.UUID,
    payload: StudioWorkflowUpdate,
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    wf = await db.get(Workflow, workflow_id)
    if not wf or wf.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if payload.name is not None:
        wf.name = payload.name
    if payload.description is not None:
        wf.description = payload.description

    if payload.visual_definition is not None:
        validation = validate_visual_workflow(payload.visual_definition)
        if not validation.valid:
            raise HTTPException(status_code=400, detail={"errors": validation.errors, "warnings": validation.warnings})

        result = await db.execute(
            select(StudioWorkflowVersion)
            .where(
                StudioWorkflowVersion.workflow_id == workflow_id,
                StudioWorkflowVersion.status == StudioVersionStatus.DRAFT,
            )
            .order_by(StudioWorkflowVersion.version.desc())
            .limit(1)
        )
        draft = result.scalar_one_or_none()
        if draft:
            draft.visual_definition = payload.visual_definition
            if payload.change_summary:
                draft.change_summary = payload.change_summary
        else:
            max_result = await db.execute(
                select(func.max(StudioWorkflowVersion.version)).where(
                    StudioWorkflowVersion.workflow_id == workflow_id
                )
            )
            next_ver = (max_result.scalar() or 0) + 1
            draft = StudioWorkflowVersion(
                workflow_id=workflow_id,
                organization_id=ctx.organization_id,
                version=next_ver,
                status=StudioVersionStatus.DRAFT,
                visual_definition=payload.visual_definition,
                change_summary=payload.change_summary or "Draft update",
                created_by=ctx.user.id,
            )
            db.add(draft)
            db.add(
                StudioVersionHistory(
                    organization_id=ctx.organization_id,
                    resource_type="workflow",
                    resource_id=workflow_id,
                    version=next_ver,
                    actor_id=ctx.user.id,
                    change_summary=payload.change_summary or "Draft update",
                )
            )
        wf.definition = {"studio": True, "visual": payload.visual_definition}

    await db.commit()
    return {"id": str(wf.id), "status": wf.status}


@router.post("/workflows/{workflow_id}/publish")
async def publish_studio_workflow(
    workflow_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    wf = await db.get(Workflow, workflow_id)
    if not wf or wf.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Workflow not found")

    result = await db.execute(
        select(StudioWorkflowVersion)
        .where(StudioWorkflowVersion.workflow_id == workflow_id, StudioWorkflowVersion.status == StudioVersionStatus.DRAFT)
        .order_by(StudioWorkflowVersion.version.desc())
        .limit(1)
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=400, detail="No draft version to publish")

    visual = version.visual_definition or {}
    validation = validate_visual_workflow(visual)
    if not validation.valid:
        raise HTTPException(status_code=400, detail={"errors": validation.errors})

    nodes = visual.get("nodes") or []
    edges = visual.get("edges") or []
    compiled = compile_visual_to_engine(nodes, edges)
    await _sync_workflow_nodes(db, wf, compiled)

    version.status = StudioVersionStatus.PUBLISHED
    version.published_at = datetime.now(UTC)
    wf.status = WorkflowStatus.ACTIVE
    wf.definition = {"studio": True, "visual": visual, "compiled_version": version.version}
    record_studio_workflow(status="published")
    await db.commit()
    return {"status": "published", "version": version.version}


@router.get("/agents")
async def list_studio_agents(
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Agent).where(Agent.organization_id == ctx.organization_id).order_by(Agent.updated_at.desc())
    )
    return [
        {
            "id": str(a.id),
            "name": a.name,
            "status": a.status,
            "max_steps": a.max_steps,
            "timeout_seconds": a.timeout_seconds,
        }
        for a in result.scalars().all()
    ]


@router.patch("/agents/{agent_id}")
async def update_studio_agent(
    agent_id: uuid.UUID,
    payload: StudioAgentConfigUpdate,
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    agent = await db.get(Agent, agent_id)
    if not agent or agent.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Agent not found")

    if payload.system_prompt is not None:
        agent.system_prompt = payload.system_prompt
    if payload.name is not None:
        agent.name = payload.name
    if payload.description is not None:
        agent.description = payload.description
    if payload.model_configuration is not None:
        agent.model_configuration = payload.model_configuration
    if payload.tool_configuration is not None:
        allowed = set(list_builtin_names())
        requested = set(payload.tool_configuration.get("allowed_tools") or [])
        invalid = requested - allowed
        if invalid:
            raise HTTPException(status_code=400, detail=f"Unauthorized tools: {sorted(invalid)}")
        agent.tool_configuration = payload.tool_configuration
    if payload.memory_configuration is not None:
        agent.memory_configuration = payload.memory_configuration
    if payload.max_steps is not None:
        agent.max_steps = min(payload.max_steps, 50)
    if payload.timeout_seconds is not None:
        agent.timeout_seconds = min(payload.timeout_seconds, 600)
    if payload.max_tokens is not None:
        agent.max_tokens = payload.max_tokens
    if payload.max_budget_usd is not None:
        agent.max_budget_usd = payload.max_budget_usd

    result = await db.execute(
        select(func.max(StudioAgentVersion.version)).where(StudioAgentVersion.agent_id == agent.id)
    )
    max_ver = result.scalar() or 0
    snapshot = {
        "name": agent.name,
        "system_prompt": agent.system_prompt,
        "model_configuration": agent.model_configuration,
        "tool_configuration": agent.tool_configuration,
        "memory_configuration": agent.memory_configuration,
        "max_steps": agent.max_steps,
        "timeout_seconds": agent.timeout_seconds,
    }
    db.add(
        StudioAgentVersion(
            agent_id=agent.id,
            organization_id=ctx.organization_id,
            version=max_ver + 1,
            status=StudioVersionStatus.DRAFT,
            config_snapshot=snapshot,
            change_summary="Studio update",
            created_by=ctx.user.id,
        )
    )
    await db.commit()
    return {"id": str(agent.id), "version": max_ver + 1}


@router.post("/compare")
async def studio_compare(
    payload: StudioCompareRequest,
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_READ)),
    db: AsyncSession = Depends(get_db),
):
    system_content = None
    if payload.prompt_version_id:
        pv = await db.get(PromptVersion, payload.prompt_version_id)
        if pv:
            from app.services.studio.workflows import substitute_prompt_variables

            system_content, errors = substitute_prompt_variables(pv.content, payload.variables)
            if errors:
                raise HTTPException(status_code=400, detail={"variable_errors": errors})

    results = []
    for model in payload.models:
        start = time.time()
        messages = [ChatMessage(role="user", content=m.get("content", "")) for m in payload.messages if m.get("role") != "system"]
        if system_content:
            messages.insert(0, ChatMessage(role="system", content=system_content))
        try:
            result = await execute_chat(
                ChatCompletionRequest(model=model, messages=messages, temperature=payload.temperature, max_tokens=payload.max_tokens),
                db,
                ctx.user,
                None,
            )
            output = result.response.choices[0].message.content if result.response.choices else ""
            usage = result.response.usage
            results.append({
                "model": model,
                "output": output,
                "latency_ms": result.latency_ms,
                "tokens": (usage.prompt_tokens + usage.completion_tokens) if usage else 0,
                "estimated_cost": result.estimated_total_cost,
                "cost_type": "estimated",
                "provider": result.provider,
            })
        except Exception as e:
            results.append({"model": model, "error": str(e)})

    return {"comparisons": results}


@router.get("/deployments")
async def list_deployments(
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(StudioDeployment)
        .where(StudioDeployment.organization_id == ctx.organization_id)
        .order_by(StudioDeployment.created_at.desc())
    )
    return [
        {
            "id": str(d.id),
            "name": d.name,
            "resource_type": d.resource_type,
            "status": d.status,
            "environment_id": str(d.environment_id) if d.environment_id else None,
            "created_at": d.created_at.isoformat(),
        }
        for d in result.scalars().all()
    ]


@router.post("/deployments", status_code=status.HTTP_201_CREATED)
async def create_deployment(
    payload: StudioDeploymentCreate,
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    dep = await DeploymentService(db).create(
        org_id=ctx.organization_id,
        name=payload.name,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        version_id=payload.version_id,
        environment_id=payload.environment_id,
        user_id=ctx.user.id,
    )
    record_studio_deployment(status="draft")
    await db.commit()
    return {"id": str(dep.id), "status": dep.status}


@router.post("/deployments/{deployment_id}/validate")
async def validate_deployment(
    deployment_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    dep = await DeploymentService(db).get(ctx.organization_id, deployment_id)
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")
    dep = await DeploymentService(db).validate(
        dep, org_id=ctx.organization_id, user_id=ctx.user.id
    )
    await db.commit()
    return {"id": str(dep.id), "status": dep.status}


@router.post("/deployments/{deployment_id}/approve")
async def approve_deployment(
    deployment_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.GOVERNANCE_APPROVE)),
    db: AsyncSession = Depends(get_db),
):
    svc = DeploymentService(db)
    dep = await svc.get(ctx.organization_id, deployment_id)
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")
    if dep.status == StudioDeploymentStatus.REJECTED:
        raise HTTPException(status_code=400, detail="Deployment rejected by quality gate")
    dep = await svc.approve(dep, ctx.user.id)
    dep = await svc.deploy(dep)
    record_studio_deployment(status="deployed")
    await db.commit()
    return {"id": str(dep.id), "status": dep.status}


@router.post("/{resource_type}/{resource_id}/comments", status_code=status.HTTP_201_CREATED)
async def add_comment(
    resource_type: str,
    resource_id: uuid.UUID,
    payload: StudioCommentCreate,
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_READ)),
    db: AsyncSession = Depends(get_db),
):
    comment = StudioComment(
        organization_id=ctx.organization_id,
        resource_type=resource_type,
        resource_id=resource_id,
        author_id=ctx.user.id,
        body=payload.body,
    )
    db.add(comment)
    await db.commit()
    return {"id": str(comment.id)}


@router.get("/history/{resource_type}/{resource_id}")
async def version_history(
    resource_type: str,
    resource_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(StudioVersionHistory)
        .where(
            StudioVersionHistory.organization_id == ctx.organization_id,
            StudioVersionHistory.resource_type == resource_type,
            StudioVersionHistory.resource_id == resource_id,
        )
        .order_by(StudioVersionHistory.version.desc())
    )
    return [
        {
            "version": h.version,
            "summary": h.change_summary,
            "actor_id": str(h.actor_id) if h.actor_id else None,
            "timestamp": h.created_at.isoformat(),
        }
        for h in result.scalars().all()
    ]


@router.post("/import")
async def import_resource(
    payload: ImportRequest,
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    errors = validate_import(payload.payload)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})
    return {"status": "validated", "resource_type": payload.payload.get("resource_type")}


@router.get("/export/{resource_type}/{resource_id}")
async def export_studio_resource(
    resource_type: str,
    resource_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_READ)),
    db: AsyncSession = Depends(get_db),
):
    data: dict = {"id": str(resource_id)}
    if resource_type == "prompt":
        p = await db.get(PromptTemplate, resource_id)
        if not p or p.organization_id != ctx.organization_id:
            raise HTTPException(status_code=404)
        data = {"name": p.name, "description": p.description, "tags": p.tags}
    elif resource_type == "workflow":
        wf = await db.get(Workflow, resource_id)
        if not wf or wf.organization_id != ctx.organization_id:
            raise HTTPException(status_code=404)
        data = {"name": wf.name, "definition": wf.definition}
    return export_resource(resource_type, data)


# ---- Prompts (also at /prompts) ----

@prompts_router.get("/", response_model=list[PromptResponse])
async def list_prompts(
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_READ)),
    db: AsyncSession = Depends(get_db),
):
    items = await PromptService(db).list_prompts(ctx.organization_id)
    return [
        PromptResponse(
            id=p.id, name=p.name, description=p.description, tags=p.tags or [],
            current_version_id=p.current_version_id, usage_count=p.usage_count,
            created_at=p.created_at, updated_at=p.updated_at,
        )
        for p in items
    ]


@prompts_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_prompt(
    payload: PromptCreate,
    ctx: OrgContext = Depends(require_permission(Permission.PROMPTS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        prompt, version = await PromptService(db).create(
            org_id=ctx.organization_id,
            name=payload.name,
            content=payload.content,
            description=payload.description,
            tags=payload.tags,
            variables=payload.variables,
            change_notes=payload.change_notes,
            user_id=ctx.user.id,
        )
        await db.commit()
        return {"id": str(prompt.id), "version_id": str(version.id), "version": version.version}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@prompts_router.get("/{prompt_id}")
async def get_prompt(
    prompt_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_READ)),
    db: AsyncSession = Depends(get_db),
):
    prompt = await PromptService(db).get(ctx.organization_id, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    versions = await PromptService(db).list_versions(prompt_id)
    return {
        "id": str(prompt.id),
        "name": prompt.name,
        "description": prompt.description,
        "tags": prompt.tags,
        "versions": [
            PromptVersionResponse(
                id=v.id, version=v.version, content=v.content,
                variables=v.variables or [], change_notes=v.change_notes, created_at=v.created_at,
            ).model_dump()
            for v in versions
        ],
    }


@prompts_router.post("/{prompt_id}/versions", status_code=status.HTTP_201_CREATED)
async def add_prompt_version(
    prompt_id: uuid.UUID,
    payload: PromptVersionCreate,
    ctx: OrgContext = Depends(require_permission(Permission.PROMPTS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    prompt = await PromptService(db).get(ctx.organization_id, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    try:
        version = await PromptService(db).add_version(
            prompt, content=payload.content, variables=payload.variables,
            change_notes=payload.change_notes, user_id=ctx.user.id,
        )
        await db.commit()
        return {"version_id": str(version.id), "version": version.version}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@prompts_router.post("/{prompt_id}/test")
async def test_prompt(
    prompt_id: uuid.UUID,
    payload: PromptTestRequest,
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_READ)),
    db: AsyncSession = Depends(get_db),
):
    prompt = await PromptService(db).get(ctx.organization_id, prompt_id)
    if not prompt or not prompt.current_version_id:
        raise HTTPException(status_code=404, detail="Prompt not found")
    version = await db.get(PromptVersion, prompt.current_version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    try:
        result = await PromptService(db).test_prompt(
            version, user=ctx.user, db=db, input_text=payload.input,
            variables=payload.variables, model=payload.model, parameters=payload.parameters,
        )
        prompt.usage_count += 1
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ---- Evaluations ----

@evaluations_router.get("/datasets", response_model=list[DatasetResponse])
async def list_datasets(
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EvaluationDataset)
        .where(EvaluationDataset.organization_id == ctx.organization_id)
        .order_by(EvaluationDataset.updated_at.desc())
    )
    return [
        DatasetResponse(
            id=d.id, name=d.name, description=d.description, version=d.version,
            test_case_count=len(d.test_cases or []), created_at=d.created_at,
        )
        for d in result.scalars().all()
    ]


@evaluations_router.post("/datasets", status_code=status.HTTP_201_CREATED)
async def create_dataset(
    payload: DatasetCreate,
    ctx: OrgContext = Depends(require_permission(Permission.EVALUATIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    dataset = EvaluationDataset(
        organization_id=ctx.organization_id,
        name=payload.name,
        description=payload.description,
        test_cases=payload.test_cases,
        created_by=ctx.user.id,
    )
    db.add(dataset)
    await db.commit()
    return {"id": str(dataset.id)}


@evaluations_router.get("/")
async def list_evaluation_suites(
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EvaluationSuite)
        .where(EvaluationSuite.organization_id == ctx.organization_id)
        .order_by(EvaluationSuite.created_at.desc())
    )
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "description": s.description,
            "model": s.model,
            "dataset_id": str(s.dataset_id),
        }
        for s in result.scalars().all()
    ]


@evaluations_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_evaluation_suite(
    payload: EvaluationSuiteCreate,
    ctx: OrgContext = Depends(require_permission(Permission.EVALUATIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    suite = EvaluationSuite(
        organization_id=ctx.organization_id,
        name=payload.name,
        description=payload.description,
        dataset_id=payload.dataset_id,
        prompt_version_id=payload.prompt_version_id,
        model=payload.model,
        parameters=payload.parameters,
        scorers=payload.scorers,
        created_by=ctx.user.id,
    )
    db.add(suite)
    await db.commit()
    return {"id": str(suite.id)}


@evaluations_router.post("/{suite_id}/run", response_model=EvaluationRunResponse)
async def run_evaluation(
    suite_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.EVALUATIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    suite = await db.get(EvaluationSuite, suite_id)
    if not suite or suite.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Evaluation suite not found")
    try:
        run = await EvaluationService(db).run_suite(suite, org_id=ctx.organization_id, user_id=ctx.user.id)
        await db.commit()
        total = run.pass_count + run.fail_count
        return EvaluationRunResponse(
            id=run.id, suite_id=run.suite_id, status=run.status,
            pass_count=run.pass_count, fail_count=run.fail_count,
            total_latency_ms=run.total_latency_ms, total_tokens=run.total_tokens,
            pass_rate=run.pass_count / total if total else None,
            started_at=run.started_at, completed_at=run.completed_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@evaluations_router.get("/runs/{run_id}", response_model=EvaluationRunResponse)
async def get_evaluation_run(
    run_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_READ)),
    db: AsyncSession = Depends(get_db),
):
    run = await EvaluationService(db).get_run(ctx.organization_id, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    total = run.pass_count + run.fail_count
    return EvaluationRunResponse(
        id=run.id, suite_id=run.suite_id, status=run.status,
        pass_count=run.pass_count, fail_count=run.fail_count,
        total_latency_ms=run.total_latency_ms, total_tokens=run.total_tokens,
        pass_rate=run.pass_count / total if total else None,
        started_at=run.started_at, completed_at=run.completed_at,
    )


@evaluations_router.get("/runs/{run_id}/results", response_model=list[EvaluationResultResponse])
async def get_evaluation_results(
    run_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_READ)),
    db: AsyncSession = Depends(get_db),
):
    run = await EvaluationService(db).get_run(ctx.organization_id, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    results = await EvaluationService(db).list_results(run_id)
    return [
        EvaluationResultResponse(
            case_index=r.case_index, input_text=r.input_text, expected=r.expected,
            actual_output=r.actual_output, passed=r.passed, scorer=r.scorer,
            score_detail=r.score_detail, latency_ms=r.latency_ms,
        )
        for r in results
    ]


@evaluation_runs_router.get("/{run_id}", response_model=EvaluationRunResponse)
async def get_evaluation_run_by_id(
    run_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.STUDIO_READ)),
    db: AsyncSession = Depends(get_db),
):
    return await get_evaluation_run(run_id, ctx, db)
