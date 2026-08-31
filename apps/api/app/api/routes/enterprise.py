"""Enterprise administration overview."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.org_context import OrgContext
from app.auth.rbac import Permission, require_permission
from app.db.base import get_db
from app.models.enterprise import (
    ConfigurationDeployment,
    DeploymentStatus,
    Environment,
    InstanceStatus,
    ManagedInstance,
    PolicySyncRecord,
    Project,
    SyncStatus,
    Workspace,
)
from app.schemas.enterprise import EnterpriseOverviewResponse

router = APIRouter(prefix="/enterprise", tags=["Enterprise"])


@router.get("/overview", response_model=EnterpriseOverviewResponse)
async def enterprise_overview(
    ctx: OrgContext = Depends(require_permission(Permission.ENTERPRISE_READ)),
    db: AsyncSession = Depends(get_db),
):
    org_id = ctx.organization_id
    since = datetime.now(UTC) - timedelta(days=7)

    workspaces = await db.scalar(
        select(func.count()).select_from(Workspace).where(Workspace.organization_id == org_id)
    )
    projects = await db.scalar(
        select(func.count()).select_from(Project).where(Project.organization_id == org_id)
    )
    environments = await db.scalar(
        select(func.count()).select_from(Environment).where(Environment.organization_id == org_id)
    )
    instances = await db.scalar(
        select(func.count()).select_from(ManagedInstance).where(ManagedInstance.organization_id == org_id)
    )
    healthy = await db.scalar(
        select(func.count())
        .select_from(ManagedInstance)
        .where(ManagedInstance.organization_id == org_id, ManagedInstance.status == InstanceStatus.HEALTHY)
    )
    deployments = await db.scalar(
        select(func.count())
        .select_from(ConfigurationDeployment)
        .where(ConfigurationDeployment.organization_id == org_id, ConfigurationDeployment.created_at >= since)
    )
    pending_sync = await db.scalar(
        select(func.count())
        .select_from(PolicySyncRecord)
        .where(PolicySyncRecord.organization_id == org_id, PolicySyncRecord.status == SyncStatus.PENDING)
    )

    return EnterpriseOverviewResponse(
        workspaces=workspaces or 0,
        projects=projects or 0,
        environments=environments or 0,
        instances=instances or 0,
        healthy_instances=healthy or 0,
        recent_deployments=deployments or 0,
        pending_policy_syncs=pending_sync or 0,
    )
