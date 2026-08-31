"""Global cloud health aggregation."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.cloud import CloudIncident, IncidentStatus, Region, RegionStatus, ServiceRegistration
from app.models.enterprise import InstanceStatus, ManagedInstance
from app.models.provider import Provider, ProviderStatus
from app.services.cloud.regions import RegionService


class CloudHealthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def platform_health(self) -> dict:
        regions = await RegionService(self.db).list_regions(include_disabled=True)
        region_health = []
        for region in regions:
            services = await self.db.execute(
                select(ServiceRegistration).where(ServiceRegistration.region_id == region.id)
            )
            svc_list = list(services.scalars().all())
            region_health.append({
                "region_id": str(region.id),
                "code": region.code,
                "status": region.status,
                "services": len(svc_list),
                "healthy_services": sum(1 for s in svc_list if s.health_status == "healthy"),
            })

        provider_counts = await self.db.execute(
            select(Provider.status, func.count()).group_by(Provider.status)
        )
        providers = {row[0]: row[1] for row in provider_counts.all()}

        open_incidents = await self.db.execute(
            select(func.count()).where(CloudIncident.status != IncidentStatus.RESOLVED)
        )
        incidents_open = int(open_incidents.scalar_one())

        overall = "healthy"
        if any(r.status == RegionStatus.DISABLED for r in regions):
            overall = "degraded"
        if providers.get(ProviderStatus.OFFLINE, 0) > 0:
            overall = "degraded"
        if incidents_open > 0:
            overall = "degraded"

        return {
            "status": overall,
            "deployment_region": self.settings.deployment_region,
            "plane_type": self.settings.plane_type,
            "regions": region_health,
            "providers": providers,
            "open_incidents": incidents_open,
            "note": "Aggregates registered metadata; physical multi-region deployment requires configured regions and instances.",
        }

    async def org_cloud_health(self, organization_id: uuid.UUID) -> dict:
        instances = await self.db.execute(
            select(ManagedInstance).where(ManagedInstance.organization_id == organization_id)
        )
        inst_list = list(instances.scalars().all())
        by_status = {}
        for inst in inst_list:
            by_status[inst.status] = by_status.get(inst.status, 0) + 1

        return {
            "organization_id": str(organization_id),
            "instances_total": len(inst_list),
            "instances_by_status": by_status,
            "healthy_instances": by_status.get(InstanceStatus.HEALTHY, 0),
            "offline_instances": by_status.get(InstanceStatus.OFFLINE, 0),
        }
