"""Project and environment APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.org_context import OrgContext
from app.auth.rbac import Permission, require_permission
from app.db.base import get_db
from app.models.enterprise import (
    ActivityEvent,
    ConfigurationVersion,
    Environment,
    EnvironmentKind,
    Project,
    ProjectMember,
    ProjectRole,
    ProjectStatus,
    WorkspaceRole,
)
from app.schemas.enterprise import (
    ActivityResponse,
    CompareRequest,
    ConfigVersionCreate,
    ConfigVersionResponse,
    DeploymentResponse,
    EnvironmentResponse,
    ProjectCreate,
    ProjectMemberAdd,
    ProjectResponse,
    ProjectUpdate,
    PromoteRequest,
)
from app.services.enterprise.access import (
    assert_project_access,
    assert_workspace_access,
    get_project,
    get_workspace,
)
from app.services.enterprise.activity import record_activity
from app.services.enterprise.config import ConfigurationService

router = APIRouter(prefix="/projects", tags=["Projects"])


def _env_response(env: Environment) -> EnvironmentResponse:
    active = next((v.version for v in (env.configuration_versions or []) if v.is_active), None)
    return EnvironmentResponse(
        id=env.id,
        project_id=env.project_id,
        name=env.name,
        slug=env.slug,
        kind=env.kind,
        is_protected=env.is_protected,
        active_config_version=active,
        created_at=env.created_at,
    )


async def _create_default_environments(db: AsyncSession, project: Project) -> None:
    defaults = [
        ("Development", "development", EnvironmentKind.DEVELOPMENT, False),
        ("Staging", "staging", EnvironmentKind.STAGING, False),
        ("Production", "production", EnvironmentKind.PRODUCTION, True),
    ]
    for name, slug, kind, protected in defaults:
        db.add(
            Environment(
                organization_id=project.organization_id,
                project_id=project.id,
                name=name,
                slug=slug,
                kind=kind,
                is_protected=protected,
            )
        )


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    ctx: OrgContext = Depends(require_permission(Permission.ENTERPRISE_READ)),
    db: AsyncSession = Depends(get_db),
    workspace_id: uuid.UUID | None = None,
):
    q = select(Project).where(
        Project.organization_id == ctx.organization_id,
        Project.status == ProjectStatus.ACTIVE,
    )
    if workspace_id:
        q = q.where(Project.workspace_id == workspace_id)
    result = await db.execute(q.order_by(Project.name))
    projects = list(result.scalars().all())
    if ctx.role.value not in {"owner", "admin"}:
        filtered = []
        for p in projects:
            try:
                await assert_project_access(db, p, ctx.user.id, ctx.role)
                filtered.append(p)
            except HTTPException:
                continue
        projects = filtered
    return [ProjectResponse.model_validate(p) for p in projects]


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    payload: ProjectCreate,
    ctx: OrgContext = Depends(require_permission(Permission.ENTERPRISE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    ws = await get_workspace(db, ctx.organization_id, payload.workspace_id)
    await assert_workspace_access(db, ws, ctx.user.id, ctx.role, min_role=WorkspaceRole.MEMBER)
    project = Project(
        organization_id=ctx.organization_id,
        workspace_id=ws.id,
        name=payload.name,
        description=payload.description,
        is_restricted=payload.is_restricted,
        created_by=ctx.user.id,
    )
    db.add(project)
    await db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=ctx.user.id, role=ProjectRole.ADMIN))
    await _create_default_environments(db, project)
    await record_activity(
        db,
        organization_id=ctx.organization_id,
        workspace_id=ws.id,
        project_id=project.id,
        event_type="project.created",
        resource_type="project",
        resource_id=str(project.id),
        actor_id=ctx.user.id,
    )
    await db.commit()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project_detail(
    project_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.ENTERPRISE_READ)),
    db: AsyncSession = Depends(get_db),
):
    project = await get_project(db, ctx.organization_id, project_id)
    await assert_project_access(db, project, ctx.user.id, ctx.role)
    return ProjectResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    ctx: OrgContext = Depends(require_permission(Permission.ENTERPRISE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    project = await get_project(db, ctx.organization_id, project_id)
    await assert_project_access(db, project, ctx.user.id, ctx.role, min_role=ProjectRole.ADMIN)
    for key, val in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, val)
    await record_activity(
        db,
        organization_id=ctx.organization_id,
        project_id=project.id,
        event_type="project.updated",
        actor_id=ctx.user.id,
    )
    await db.commit()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.post("/{project_id}/members", status_code=201)
async def add_project_member(
    project_id: uuid.UUID,
    payload: ProjectMemberAdd,
    ctx: OrgContext = Depends(require_permission(Permission.ENTERPRISE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    project = await get_project(db, ctx.organization_id, project_id)
    await assert_project_access(db, project, ctx.user.id, ctx.role, min_role=ProjectRole.ADMIN)
    db.add(ProjectMember(project_id=project.id, user_id=payload.user_id, role=payload.role))
    await db.commit()
    return {"status": "ok"}


@router.get("/{project_id}/environments", response_model=list[EnvironmentResponse])
async def list_environments(
    project_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.ENTERPRISE_READ)),
    db: AsyncSession = Depends(get_db),
):
    project = await get_project(db, ctx.organization_id, project_id)
    await assert_project_access(db, project, ctx.user.id, ctx.role)
    result = await db.execute(
        select(Environment)
        .options(selectinload(Environment.configuration_versions))
        .where(Environment.project_id == project.id)
        .order_by(Environment.slug)
    )
    return [_env_response(e) for e in result.scalars().all()]


@router.get("/{project_id}/activity", response_model=list[ActivityResponse])
async def project_activity(
    project_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.ENTERPRISE_READ)),
    db: AsyncSession = Depends(get_db),
):
    project = await get_project(db, ctx.organization_id, project_id)
    await assert_project_access(db, project, ctx.user.id, ctx.role)
    result = await db.execute(
        select(ActivityEvent)
        .where(ActivityEvent.project_id == project.id)
        .order_by(ActivityEvent.created_at.desc())
        .limit(50)
    )
    return [
        ActivityResponse(
            id=e.id,
            event_type=e.event_type,
            resource_type=e.resource_type,
            resource_id=e.resource_id,
            actor_id=e.actor_id,
            safe_metadata=e.safe_metadata,
            created_at=e.created_at,
        )
        for e in result.scalars().all()
    ]


env_router = APIRouter(prefix="/environments", tags=["Environments"])


@env_router.get("/{environment_id}", response_model=EnvironmentResponse)
async def get_environment(
    environment_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.ENTERPRISE_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Environment)
        .options(selectinload(Environment.configuration_versions))
        .where(Environment.id == environment_id, Environment.organization_id == ctx.organization_id)
    )
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    project = await get_project(db, ctx.organization_id, env.project_id)
    await assert_project_access(db, project, ctx.user.id, ctx.role)
    return _env_response(env)


@env_router.post("/{environment_id}/configurations", response_model=ConfigVersionResponse, status_code=201)
async def create_config_version(
    environment_id: uuid.UUID,
    payload: ConfigVersionCreate,
    ctx: OrgContext = Depends(require_permission(Permission.ENTERPRISE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Environment).where(Environment.id == environment_id, Environment.organization_id == ctx.organization_id)
    )
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    project = await get_project(db, ctx.organization_id, env.project_id)
    await assert_project_access(db, project, ctx.user.id, ctx.role, min_role=ProjectRole.ADMIN)

    svc = ConfigurationService(db)
    version = await svc.create_version(
        env,
        payload.config,
        secret_refs=payload.secret_refs,
        change_summary=payload.change_summary,
        author_id=ctx.user.id,
        activate=payload.activate,
    )
    await record_activity(
        db,
        organization_id=ctx.organization_id,
        project_id=project.id,
        event_type="configuration.created",
        resource_type="configuration_version",
        resource_id=str(version.id),
        actor_id=ctx.user.id,
        metadata={"version": version.version, "environment": env.slug},
    )
    await db.commit()
    return ConfigVersionResponse.model_validate(version)


@env_router.post("/{environment_id}/promote", response_model=ConfigVersionResponse)
async def promote_environment(
    environment_id: uuid.UUID,
    payload: PromoteRequest,
    ctx: OrgContext = Depends(require_permission(Permission.ENTERPRISE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    source = await db.get(Environment, environment_id)
    target = await db.get(Environment, payload.target_environment_id)
    if not source or not target or source.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Environment not found")
    if source.project_id != target.project_id:
        raise HTTPException(status_code=400, detail="Environments must belong to same project")

    svc = ConfigurationService(db)
    try:
        version = await svc.promote(
            source,
            target,
            author_id=ctx.user.id,
            require_approval=payload.require_approval,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    await record_activity(
        db,
        organization_id=ctx.organization_id,
        project_id=source.project_id,
        event_type="environment.promoted",
        metadata={"from": source.slug, "to": target.slug, "version": version.version},
        actor_id=ctx.user.id,
    )
    await db.commit()
    return ConfigVersionResponse.model_validate(version)


@env_router.post("/configurations/compare")
async def compare_configurations(
    payload: CompareRequest,
    ctx: OrgContext = Depends(require_permission(Permission.ENTERPRISE_READ)),
    db: AsyncSession = Depends(get_db),
):
    svc = ConfigurationService(db)
    try:
        return await svc.compare_versions(payload.version_a_id, payload.version_b_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@env_router.post("/{environment_id}/configurations/{version_id}/rollback", response_model=ConfigVersionResponse)
async def rollback_configuration(
    environment_id: uuid.UUID,
    version_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.ENTERPRISE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    env = await db.get(Environment, environment_id)
    if not env or env.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Environment not found")
    project = await get_project(db, ctx.organization_id, env.project_id)
    await assert_project_access(db, project, ctx.user.id, ctx.role, min_role=ProjectRole.ADMIN)

    svc = ConfigurationService(db)
    try:
        version = await svc.rollback(env, version_id, author_id=ctx.user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await record_activity(
        db,
        organization_id=ctx.organization_id,
        project_id=project.id,
        event_type="configuration.rollback",
        actor_id=ctx.user.id,
    )
    await db.commit()
    return ConfigVersionResponse.model_validate(version)


@env_router.post("/{environment_id}/deploy/{version_id}", response_model=DeploymentResponse)
async def deploy_configuration(
    environment_id: uuid.UUID,
    version_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.ENTERPRISE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    env = await db.get(Environment, environment_id)
    version = await db.get(ConfigurationVersion, version_id)
    if not env or not version or env.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Not found")
    if version.environment_id != env.id:
        raise HTTPException(status_code=400, detail="Version does not belong to environment")

    svc = ConfigurationService(db)
    deployment = await svc.deploy(
        org_id=ctx.organization_id,
        config_version=version,
        environment_id=env.id,
        deployed_by=ctx.user.id,
        idempotency_key=f"{env.id}:{version.id}",
    )
    await record_activity(
        db,
        organization_id=ctx.organization_id,
        project_id=env.project_id,
        event_type="configuration.deployed",
        metadata={"deployment_id": str(deployment.id), "status": deployment.status},
        actor_id=ctx.user.id,
    )
    await db.commit()
    return DeploymentResponse.model_validate(deployment)
