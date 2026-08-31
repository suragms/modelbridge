"""Cloud incident management."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud import CloudIncident, IncidentStatus


class IncidentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_incidents(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[CloudIncident]:
        q = select(CloudIncident).order_by(CloudIncident.started_at.desc()).limit(limit)
        if organization_id:
            q = q.where(CloudIncident.organization_id == organization_id)
        if status:
            q = q.where(CloudIncident.status == status)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def create(
        self,
        *,
        title: str,
        severity: str,
        organization_id: uuid.UUID | None = None,
        region_id: uuid.UUID | None = None,
        description: str | None = None,
        affected_service: str | None = None,
        created_by: uuid.UUID | None = None,
    ) -> CloudIncident:
        incident = CloudIncident(
            organization_id=organization_id,
            region_id=region_id,
            title=title,
            description=description,
            severity=severity,
            status=IncidentStatus.OPEN,
            affected_service=affected_service,
            created_by=created_by,
        )
        self.db.add(incident)
        await self.db.flush()
        return incident

    async def update_status(
        self,
        incident: CloudIncident,
        status: str,
    ) -> CloudIncident:
        incident.status = status
        if status == IncidentStatus.RESOLVED:
            incident.resolved_at = datetime.now(UTC)
        await self.db.flush()
        return incident
