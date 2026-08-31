"""Service discovery abstraction."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.cloud import Region, ServiceHealth, ServiceRegistration

STALE_SECONDS = 300


class ServiceDiscovery:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def register(
        self,
        *,
        service_name: str,
        region_id: uuid.UUID,
        endpoint: str,
        plane_type: str = "data",
        capabilities: list[str] | None = None,
        health_status: str = ServiceHealth.HEALTHY,
    ) -> ServiceRegistration:
        existing = await self.db.execute(
            select(ServiceRegistration).where(
                ServiceRegistration.service_name == service_name,
                ServiceRegistration.region_id == region_id,
            )
        )
        reg = existing.scalar_one_or_none()
        now = datetime.now(UTC)
        if reg:
            reg.endpoint = endpoint.rstrip("/")
            reg.plane_type = plane_type
            reg.capabilities = capabilities or []
            reg.health_status = health_status
            reg.last_seen_at = now
        else:
            reg = ServiceRegistration(
                service_name=service_name,
                region_id=region_id,
                endpoint=endpoint.rstrip("/"),
                plane_type=plane_type,
                capabilities=capabilities or [],
                health_status=health_status,
                last_seen_at=now,
            )
            self.db.add(reg)
        await self.db.flush()
        return reg

    async def discover(
        self,
        service_name: str,
        *,
        region_id: uuid.UUID | None = None,
        healthy_only: bool = True,
    ) -> list[ServiceRegistration]:
        q = select(ServiceRegistration).where(ServiceRegistration.service_name == service_name)
        if region_id:
            q = q.where(ServiceRegistration.region_id == region_id)
        result = await self.db.execute(q)
        services = list(result.scalars().all())
        if healthy_only:
            cutoff = datetime.now(UTC) - timedelta(seconds=STALE_SECONDS)
            services = [
                s
                for s in services
                if s.health_status in {ServiceHealth.HEALTHY, ServiceHealth.DEGRADED}
                and s.last_seen_at
                and s.last_seen_at >= cutoff
            ]
        return services

    async def local_endpoint(self, service_name: str = "modelbridge-api") -> str | None:
        """Return local deployment endpoint from settings when registry is empty."""
        settings = self.settings
        base = f"http://{settings.api_host}:{settings.api_port}"
        if settings.api_host == "0.0.0.0":
            base = f"http://localhost:{settings.api_port}"
        return base

    async def resolve_endpoint(
        self,
        service_name: str,
        *,
        region: Region | None = None,
    ) -> str | None:
        region_id = region.id if region else None
        services = await self.discover(service_name, region_id=region_id)
        if services:
            return services[0].endpoint
        if region and region.code == self.settings.deployment_region:
            return await self.local_endpoint(service_name)
        return None
