"""Usage metering events and aggregation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud import UsageEventType, UsageMeterEvent

SAFE_METADATA_KEYS = frozenset({
    "provider",
    "model",
    "endpoint",
    "status",
    "region_code",
    "plane_type",
})


def sanitize_metadata(metadata: dict | None) -> dict | None:
    if not metadata:
        return None
    return {k: v for k, v in metadata.items() if k in SAFE_METADATA_KEYS}


class MeteringService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record(
        self,
        *,
        organization_id: uuid.UUID,
        event_type: str,
        quantity: float = 1.0,
        workspace_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        environment_id: uuid.UUID | None = None,
        metadata: dict | None = None,
    ) -> UsageMeterEvent:
        event = UsageMeterEvent(
            organization_id=organization_id,
            workspace_id=workspace_id,
            project_id=project_id,
            environment_id=environment_id,
            event_type=event_type,
            quantity=quantity,
            safe_metadata=sanitize_metadata(metadata),
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def aggregate(
        self,
        organization_id: uuid.UUID,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        workspace_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        environment_id: uuid.UUID | None = None,
    ) -> dict:
        since = since or datetime.now(UTC) - timedelta(days=30)
        until = until or datetime.now(UTC)

        q = select(
            UsageMeterEvent.event_type,
            func.sum(UsageMeterEvent.quantity).label("total"),
        ).where(
            UsageMeterEvent.organization_id == organization_id,
            UsageMeterEvent.recorded_at >= since,
            UsageMeterEvent.recorded_at <= until,
        )
        if workspace_id:
            q = q.where(UsageMeterEvent.workspace_id == workspace_id)
        if project_id:
            q = q.where(UsageMeterEvent.project_id == project_id)
        if environment_id:
            q = q.where(UsageMeterEvent.environment_id == environment_id)

        q = q.group_by(UsageMeterEvent.event_type)
        result = await self.db.execute(q)
        by_type = {row.event_type: float(row.total) for row in result.all()}

        return {
            "organization_id": str(organization_id),
            "period_start": since.isoformat(),
            "period_end": until.isoformat(),
            "totals": by_type,
            "requests": by_type.get(UsageEventType.REQUEST, 0),
            "tokens": by_type.get(UsageEventType.TOKENS, 0),
            "agent_executions": by_type.get(UsageEventType.AGENT_EXECUTION, 0),
            "workflow_executions": by_type.get(UsageEventType.WORKFLOW_EXECUTION, 0),
        }
