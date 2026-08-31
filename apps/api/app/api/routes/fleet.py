"""Fleet management and control-plane instance APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.org_context import OrgContext
from app.auth.rbac import Permission, require_permission
from app.db.base import get_db
from app.models.enterprise import ConfigurationVersion, InstanceHeartbeat, ManagedInstance, SyncStatus
from app.models.governance import GovernancePolicy, PolicyStatus
from app.schemas.enterprise import (
    HeartbeatRequest,
    InstanceRegisterRequest,
    InstanceRegisterResponse,
    InstanceResponse,
)
from app.services.enterprise.activity import record_activity
from app.services.enterprise.fleet import FleetService

router = APIRouter(prefix="/fleet", tags=["Fleet"])
control_router = APIRouter(prefix="/control-plane", tags=["Control Plane"])


def _instance_response(inst: ManagedInstance) -> InstanceResponse:
    return InstanceResponse(
        id=inst.id,
        organization_id=inst.organization_id,
        name=inst.name,
        endpoint=inst.endpoint,
        environment_kind=inst.environment_kind,
        status=inst.status,
        version=inst.version,
        capabilities=list(inst.capabilities or []),
        last_seen_at=inst.last_seen_at,
        created_at=inst.created_at,
    )


@router.get("")
async def list_fleet(
    ctx: OrgContext = Depends(require_permission(Permission.FLEET_READ)),
    db: AsyncSession = Depends(get_db),
):
    svc = FleetService(db)
    overview = await svc.fleet_overview(ctx.organization_id)
    await db.commit()
    return overview


@router.post("/register", response_model=InstanceRegisterResponse, status_code=201)
async def register_instance(
    payload: InstanceRegisterRequest,
    ctx: OrgContext = Depends(require_permission(Permission.FLEET_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    svc = FleetService(db)
    instance, token = await svc.register(
        org_id=ctx.organization_id,
        name=payload.name,
        endpoint=payload.endpoint,
        environment_kind=payload.environment_kind,
        registered_by=ctx.user.id,
    )
    await record_activity(
        db,
        organization_id=ctx.organization_id,
        event_type="instance.registered",
        resource_type="instance",
        resource_id=str(instance.id),
        actor_id=ctx.user.id,
        metadata={"name": instance.name, "endpoint": instance.endpoint},
    )
    await db.commit()
    return InstanceRegisterResponse(
        id=instance.id,
        name=instance.name,
        endpoint=instance.endpoint,
        credential=token,
        status=instance.status,
    )


@router.get("/{instance_id}", response_model=InstanceResponse)
async def get_instance(
    instance_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.FLEET_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ManagedInstance)
        .options(selectinload(ManagedInstance.heartbeats))
        .where(ManagedInstance.id == instance_id, ManagedInstance.organization_id == ctx.organization_id)
    )
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    return _instance_response(inst)


@router.get("/{instance_id}/heartbeats")
async def instance_heartbeats(
    instance_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.FLEET_READ)),
    db: AsyncSession = Depends(get_db),
):
    inst = await db.get(ManagedInstance, instance_id)
    if not inst or inst.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Instance not found")
    result = await db.execute(
        select(InstanceHeartbeat)
        .where(InstanceHeartbeat.instance_id == instance_id)
        .order_by(InstanceHeartbeat.created_at.desc())
        .limit(20)
    )
    return [
        {
            "id": str(h.id),
            "status": h.status,
            "version": h.version,
            "metrics": h.metrics_snapshot,
            "created_at": h.created_at.isoformat(),
        }
        for h in result.scalars().all()
    ]


async def _authenticate_instance(
    db: AsyncSession,
    instance_id: uuid.UUID,
    authorization: str | None,
) -> ManagedInstance:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing instance credentials")
    token = authorization[7:]
    svc = FleetService(db)
    try:
        return await svc.authenticate(instance_id, token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


@control_router.post("/instances/{instance_id}/heartbeat")
async def instance_heartbeat(
    instance_id: uuid.UUID,
    payload: HeartbeatRequest,
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    instance = await _authenticate_instance(db, instance_id, authorization)
    svc = FleetService(db)
    hb = await svc.heartbeat(
        instance,
        status=payload.status,
        version=payload.version,
        capabilities=payload.capabilities,
        metrics=payload.metrics,
    )
    await db.commit()
    return {"status": "ok", "heartbeat_id": str(hb.id)}


@control_router.get("/instances/{instance_id}/configuration")
async def get_instance_configuration(
    instance_id: uuid.UUID,
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    instance = await _authenticate_instance(db, instance_id, authorization)
    # Return latest active config for org — instances validate locally
    result = await db.execute(
        select(ConfigurationVersion)
        .where(
            ConfigurationVersion.organization_id == instance.organization_id,
            ConfigurationVersion.is_active == True,  # noqa: E712
        )
        .order_by(ConfigurationVersion.created_at.desc())
        .limit(1)
    )
    version = result.scalar_one_or_none()
    if not version:
        return {"config": {}, "secret_refs": {}, "version": 0}
    return {
        "config": version.config,
        "secret_refs": version.secret_refs,
        "version": version.version,
    }


@control_router.get("/instances/{instance_id}/policies")
async def get_instance_policies(
    instance_id: uuid.UUID,
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    instance = await _authenticate_instance(db, instance_id, authorization)
    result = await db.execute(
        select(GovernancePolicy).where(
            GovernancePolicy.organization_id == instance.organization_id,
            GovernancePolicy.status == PolicyStatus.ACTIVE,
        )
    )
    policies = result.scalars().all()
    policy_version = max((p.version for p in policies), default=0)
    return {
        "policy_version": policy_version,
        "policies": [
            {
                "id": str(p.id),
                "name": p.name,
                "action": p.action,
                "version": p.version,
                "rules": p.rules,
            }
            for p in policies
        ],
    }


@control_router.post("/instances/{instance_id}/policies/report")
async def report_policy_sync(
    instance_id: uuid.UUID,
    body: dict,
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    instance = await _authenticate_instance(db, instance_id, authorization)
    svc = FleetService(db)
    record = await svc.report_policy_sync(
        instance,
        instance_policy_version=int(body.get("instance_policy_version", 0)),
        success=bool(body.get("success", False)),
    )
    await db.commit()
    return {"sync_id": str(record.id), "status": record.status}
