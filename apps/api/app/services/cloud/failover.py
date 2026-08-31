"""Health-based failover recording (requires deployment infrastructure for automatic failover)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud import FailoverEvent
from app.services.metrics import record_failover_event


class FailoverService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record(
        self,
        *,
        source_service: str,
        target_service: str,
        reason: str,
        organization_id: uuid.UUID | None = None,
        region_id: uuid.UUID | None = None,
        verified: bool = False,
        metadata: dict | None = None,
    ) -> FailoverEvent:
        event = FailoverEvent(
            organization_id=organization_id,
            region_id=region_id,
            source_service=source_service,
            target_service=target_service,
            reason=reason,
            verified=verified,
            safe_metadata=metadata,
        )
        self.db.add(event)
        record_failover_event(verified=verified)
        await self.db.flush()
        return event

    async def select_failover_target(
        self,
        service_name: str,
        *,
        region_id: uuid.UUID | None,
        exclude_endpoint: str | None = None,
    ) -> str | None:
        """Return next healthy endpoint from service discovery registry."""
        from app.services.cloud.discovery import ServiceDiscovery

        discovery = ServiceDiscovery(self.db)
        services = await discovery.discover(service_name, region_id=region_id, healthy_only=True)
        for svc in services:
            if exclude_endpoint and svc.endpoint.rstrip("/") == exclude_endpoint.rstrip("/"):
                continue
            return svc.endpoint
        return None
