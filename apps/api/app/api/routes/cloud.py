"""Cloud administration APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.org_context import OrgContext
from app.auth.rbac import Permission, require_permission
from app.db.base import get_db
from app.models.cloud import ConfigScope
from app.models.enterprise import ManagedInstance
from app.schemas.cloud import (
    CloudHealthResponse,
    CloudInstanceProvisionRequest,
    CloudInstanceProvisionResponse,
    CloudInstanceResponse,
    IncidentCreate,
    IncidentResponse,
    IncidentUpdate,
    InstanceLifecycleRequest,
    OnboardingBootstrapRequest,
    OnboardingResponse,
    OnboardingStepRequest,
    QuotaResponse,
    QuotaUpsert,
    RegionCreate,
    RegionResponse,
    RegionUpdate,
    RolloutResponse,
    ScopedConfigCreate,
    ScopedConfigResponse,
    UsageSummaryResponse,
)
from app.services.cloud.config_scope import ConfigScopeService
from app.services.cloud.health import CloudHealthService
from app.services.cloud.incidents import IncidentService
from app.services.cloud.instances import CloudInstanceService
from app.services.cloud.metering import MeteringService
from app.services.cloud.onboarding import CloudOnboardingService
from app.services.cloud.quotas import QuotaService
from app.services.cloud.regions import RegionService
from app.services.cloud.rollouts import RolloutService
from app.services.enterprise.activity import record_activity

router = APIRouter(prefix="/cloud", tags=["Cloud"])


def _instance_response(inst: ManagedInstance) -> CloudInstanceResponse:
    return CloudInstanceResponse(
        id=inst.id,
        organization_id=inst.organization_id,
        name=inst.name,
        endpoint=inst.endpoint,
        environment_kind=inst.environment_kind,
        status=inst.status,
        lifecycle_status=getattr(inst, "lifecycle_status", "active") or "active",
        plane_type=getattr(inst, "plane_type", "data") or "data",
        region_id=getattr(inst, "region_id", None),
        version=inst.version,
        capabilities=list(inst.capabilities or []),
        last_seen_at=inst.last_seen_at,
        created_at=inst.created_at,
    )


@router.get("/health", response_model=CloudHealthResponse)
async def cloud_health(
    ctx: OrgContext = Depends(require_permission(Permission.CLOUD_READ)),
    db: AsyncSession = Depends(get_db),
):
    svc = CloudHealthService(db)
    data = await svc.platform_health()
    org = await svc.org_cloud_health(ctx.organization_id)
    data["organization"] = org
    return data


@router.get("/regions", response_model=list[RegionResponse])
async def list_regions(
    ctx: OrgContext = Depends(require_permission(Permission.CLOUD_READ)),
    db: AsyncSession = Depends(get_db),
):
    regions = await RegionService(db).list_regions()
    return regions


@router.post("/regions", response_model=RegionResponse, status_code=201)
async def create_region(
    payload: RegionCreate,
    ctx: OrgContext = Depends(require_permission(Permission.CLOUD_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    svc = RegionService(db)
    existing = await svc.get_by_code(payload.code)
    if existing:
        raise HTTPException(status_code=409, detail="Region code already exists")
    region = await svc.create(
        name=payload.name,
        code=payload.code,
        location=payload.location,
        capabilities=payload.capabilities,
        data_residency_zones=payload.data_residency_zones,
    )
    await record_activity(
        db,
        organization_id=ctx.organization_id,
        event_type="region.created",
        resource_type="region",
        resource_id=str(region.id),
        actor_id=ctx.user.id,
        metadata={"code": region.code, "name": region.name},
    )
    await db.commit()
    return region


@router.patch("/regions/{region_id}", response_model=RegionResponse)
async def update_region(
    region_id: uuid.UUID,
    payload: RegionUpdate,
    ctx: OrgContext = Depends(require_permission(Permission.CLOUD_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    svc = RegionService(db)
    region = await svc.get(region_id)
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    region = await svc.update(
        region,
        name=payload.name,
        location=payload.location,
        status=payload.status,
        capabilities=payload.capabilities,
        data_residency_zones=payload.data_residency_zones,
    )
    await record_activity(
        db,
        organization_id=ctx.organization_id,
        event_type="region.updated",
        resource_type="region",
        resource_id=str(region.id),
        actor_id=ctx.user.id,
        metadata={"status": region.status},
    )
    await db.commit()
    return region


@router.get("/instances", response_model=list[CloudInstanceResponse])
async def list_cloud_instances(
    ctx: OrgContext = Depends(require_permission(Permission.CLOUD_READ)),
    db: AsyncSession = Depends(get_db),
    region_id: uuid.UUID | None = None,
):
    instances = await CloudInstanceService(db).list_instances(ctx.organization_id, region_id=region_id)
    return [_instance_response(i) for i in instances]


@router.post("/instances", response_model=CloudInstanceProvisionResponse, status_code=201)
async def provision_instance(
    payload: CloudInstanceProvisionRequest,
    ctx: OrgContext = Depends(require_permission(Permission.CLOUD_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    svc = CloudInstanceService(db)
    instance, token = await svc.provision(
        org_id=ctx.organization_id,
        name=payload.name,
        endpoint=payload.endpoint,
        region_id=payload.region_id,
        plane_type=payload.plane_type,
        environment_kind=payload.environment_kind,
        registered_by=ctx.user.id,
    )
    await record_activity(
        db,
        organization_id=ctx.organization_id,
        event_type="instance.provisioned",
        resource_type="instance",
        resource_id=str(instance.id),
        actor_id=ctx.user.id,
        metadata={"name": instance.name, "endpoint": instance.endpoint},
    )
    await db.commit()
    return CloudInstanceProvisionResponse(instance=_instance_response(instance), credential=token)


@router.get("/instances/{instance_id}", response_model=CloudInstanceResponse)
async def get_cloud_instance(
    instance_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.CLOUD_READ)),
    db: AsyncSession = Depends(get_db),
):
    inst = await CloudInstanceService(db).get_instance(ctx.organization_id, instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    return _instance_response(inst)


@router.post("/instances/{instance_id}/lifecycle", response_model=CloudInstanceResponse)
async def transition_instance(
    instance_id: uuid.UUID,
    payload: InstanceLifecycleRequest,
    ctx: OrgContext = Depends(require_permission(Permission.CLOUD_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    svc = CloudInstanceService(db)
    inst = await svc.get_instance(ctx.organization_id, instance_id)
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    try:
        inst = await svc.transition(inst, payload.target_status, actor_id=ctx.user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await db.commit()
    return _instance_response(inst)


@router.get("/incidents", response_model=list[IncidentResponse])
async def list_incidents(
    ctx: OrgContext = Depends(require_permission(Permission.CLOUD_READ)),
    db: AsyncSession = Depends(get_db),
    status: str | None = None,
):
    incidents = await IncidentService(db).list_incidents(
        organization_id=ctx.organization_id,
        status=status,
    )
    return incidents


@router.post("/incidents", response_model=IncidentResponse, status_code=201)
async def create_incident(
    payload: IncidentCreate,
    ctx: OrgContext = Depends(require_permission(Permission.CLOUD_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    incident = await IncidentService(db).create(
        title=payload.title,
        severity=payload.severity,
        organization_id=ctx.organization_id,
        region_id=payload.region_id,
        description=payload.description,
        affected_service=payload.affected_service,
        created_by=ctx.user.id,
    )
    await db.commit()
    return incident


@router.patch("/incidents/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: uuid.UUID,
    payload: IncidentUpdate,
    ctx: OrgContext = Depends(require_permission(Permission.CLOUD_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    from app.models.cloud import CloudIncident

    incident = await db.get(CloudIncident, incident_id)
    if not incident or incident.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident = await IncidentService(db).update_status(incident, payload.status)
    await db.commit()
    return incident


@router.get("/rollouts", response_model=list[RolloutResponse])
async def list_rollouts(
    ctx: OrgContext = Depends(require_permission(Permission.CLOUD_READ)),
    db: AsyncSession = Depends(get_db),
):
    rollouts = await RolloutService(db).list_rollouts(organization_id=ctx.organization_id)
    return rollouts


@router.get("/onboarding", response_model=OnboardingResponse)
async def get_onboarding(
    ctx: OrgContext = Depends(require_permission(Permission.CLOUD_READ)),
    db: AsyncSession = Depends(get_db),
):
    record = await CloudOnboardingService(db).get_or_create(ctx.organization_id)
    await db.commit()
    return record


@router.post("/onboarding/step", response_model=OnboardingResponse)
async def complete_onboarding_step(
    payload: OnboardingStepRequest,
    ctx: OrgContext = Depends(require_permission(Permission.CLOUD_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    svc = CloudOnboardingService(db)
    record = await svc.get_or_create(ctx.organization_id)
    try:
        record = await svc.complete_step(
            record,
            payload.step,
            selected_region_id=payload.selected_region_id,
            data_residency_policy=payload.data_residency_policy,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await db.commit()
    return record


@router.post("/onboarding/bootstrap")
async def bootstrap_onboarding(
    payload: OnboardingBootstrapRequest,
    ctx: OrgContext = Depends(require_permission(Permission.CLOUD_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    result = await CloudOnboardingService(db).bootstrap_workspace(
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        workspace_name=payload.workspace_name,
        project_name=payload.project_name,
    )
    await record_activity(
        db,
        organization_id=ctx.organization_id,
        event_type="cloud.onboarding.bootstrap",
        actor_id=ctx.user.id,
        metadata={"workspace_id": result["workspace_id"], "project_id": result["project_id"]},
    )
    await db.commit()
    return {
        "workspace_id": result["workspace_id"],
        "project_id": result["project_id"],
        "onboarding": OnboardingResponse.model_validate(result["onboarding"]),
    }


@router.post("/config", response_model=ScopedConfigResponse, status_code=201)
async def create_scoped_config(
    payload: ScopedConfigCreate,
    ctx: OrgContext = Depends(require_permission(Permission.CLOUD_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    org_id = ctx.organization_id if payload.scope != ConfigScope.GLOBAL else None
    if payload.scope != ConfigScope.GLOBAL and not payload.scope_ref_id:
        raise HTTPException(status_code=400, detail="scope_ref_id required for non-global scopes")
    version = await ConfigScopeService(db).create_version(
        scope=payload.scope,
        scope_ref_id=payload.scope_ref_id,
        organization_id=org_id,
        config=payload.config,
        change_summary=payload.change_summary,
        author_id=ctx.user.id,
        activate=payload.activate,
    )
    await db.commit()
    return version


@router.get("/config/resolved")
async def resolve_config(
    ctx: OrgContext = Depends(require_permission(Permission.CLOUD_READ)),
    db: AsyncSession = Depends(get_db),
    workspace_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    environment_id: uuid.UUID | None = None,
):
    merged = await ConfigScopeService(db).resolve(
        organization_id=ctx.organization_id,
        workspace_id=workspace_id,
        project_id=project_id,
        environment_id=environment_id,
    )
    return {"config": merged}


@router.post("/config/{config_id}/rollout", response_model=RolloutResponse, status_code=201)
async def rollout_config(
    config_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.CLOUD_MANAGE)),
    db: AsyncSession = Depends(get_db),
    region_id: uuid.UUID | None = None,
):
    from app.models.cloud import ScopedConfiguration

    cfg = await db.get(ScopedConfiguration, config_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Configuration not found")
    if cfg.organization_id and cfg.organization_id != ctx.organization_id:
        raise HTTPException(status_code=403, detail="Cross-organization access denied")
    rollout = await RolloutService(db).create_rollout(
        organization_id=ctx.organization_id,
        scoped_configuration=cfg,
        configuration_version_id=None,
        region_id=region_id,
        configuration_version=cfg.version,
        deployed_by=ctx.user.id,
    )
    await record_activity(
        db,
        organization_id=ctx.organization_id,
        event_type="config.rollout",
        resource_type="configuration",
        resource_id=str(cfg.id),
        actor_id=ctx.user.id,
        metadata={"region_id": str(region_id) if region_id else None, "status": rollout.status},
    )
    await db.commit()
    return rollout


usage_router = APIRouter(prefix="/usage", tags=["Usage"])


@usage_router.get("/summary", response_model=UsageSummaryResponse)
async def usage_summary(
    ctx: OrgContext = Depends(require_permission(Permission.USAGE_READ)),
    db: AsyncSession = Depends(get_db),
):
    summary = await MeteringService(db).aggregate(ctx.organization_id)
    return summary


quotas_router = APIRouter(prefix="/quotas", tags=["Quotas"])


@quotas_router.get("", response_model=list[QuotaResponse])
async def list_quotas(
    ctx: OrgContext = Depends(require_permission(Permission.USAGE_READ)),
    db: AsyncSession = Depends(get_db),
):
    svc = QuotaService(db)
    quotas = await svc.list_quotas(ctx.organization_id)
    out = []
    for q in quotas:
        usage = await svc.usage_in_period(ctx.organization_id, q)
        check = await svc.check(ctx.organization_id, q.resource)
        out.append(
            QuotaResponse(
                id=q.id,
                organization_id=q.organization_id,
                resource=q.resource,
                period=q.period,
                limit_value=q.limit_value,
                is_enabled=q.is_enabled,
                current_usage=usage,
                allowed=check["allowed"],
            )
        )
    return out


@quotas_router.put("", response_model=QuotaResponse)
async def upsert_quota(
    payload: QuotaUpsert,
    ctx: OrgContext = Depends(require_permission(Permission.QUOTA_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    svc = QuotaService(db)
    quota = await svc.upsert(
        organization_id=ctx.organization_id,
        resource=payload.resource,
        period=payload.period,
        limit_value=payload.limit_value,
        is_enabled=payload.is_enabled,
    )
    usage = await svc.usage_in_period(ctx.organization_id, quota)
    check = await svc.check(ctx.organization_id, quota.resource)
    await db.commit()
    return QuotaResponse(
        id=quota.id,
        organization_id=quota.organization_id,
        resource=quota.resource,
        period=quota.period,
        limit_value=quota.limit_value,
        is_enabled=quota.is_enabled,
        current_usage=usage,
        allowed=check["allowed"],
    )
