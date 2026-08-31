"""Activity timeline for workspaces and projects."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enterprise import ActivityEvent
from app.services.audit import _sanitize_metadata


async def record_activity(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    event_type: str,
    workspace_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    actor_id: uuid.UUID | None = None,
    metadata: dict | None = None,
) -> ActivityEvent:
    event = ActivityEvent(
        organization_id=organization_id,
        workspace_id=workspace_id,
        project_id=project_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        actor_id=actor_id,
        safe_metadata=_sanitize_metadata(metadata),
    )
    db.add(event)
    await db.flush()
    return event
