"""Event catalog and emission."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform import EVENT_SCHEMA_VERSION, PlatformEvent

EVENT_CATALOG: dict[str, dict] = {
    "request.completed": {"description": "Gateway request completed successfully", "category": "gateway"},
    "request.failed": {"description": "Gateway request failed", "category": "gateway"},
    "provider.degraded": {"description": "Provider health degraded", "category": "provider"},
    "provider.recovered": {"description": "Provider health recovered", "category": "provider"},
    "agent.started": {"description": "Agent execution started", "category": "agent"},
    "agent.completed": {"description": "Agent execution completed", "category": "agent"},
    "agent.failed": {"description": "Agent execution failed", "category": "agent"},
    "workflow.started": {"description": "Workflow execution started", "category": "workflow"},
    "workflow.completed": {"description": "Workflow execution completed", "category": "workflow"},
    "workflow.failed": {"description": "Workflow execution failed", "category": "workflow"},
    "deployment.started": {"description": "Configuration deployment started", "category": "deployment"},
    "deployment.completed": {"description": "Configuration deployment completed", "category": "deployment"},
    "deployment.failed": {"description": "Configuration deployment failed", "category": "deployment"},
    "anomaly.detected": {"description": "Intelligence anomaly detected", "category": "intelligence"},
    "recommendation.created": {"description": "Intelligence recommendation created", "category": "intelligence"},
    "webhook.delivery.failed": {"description": "Outbound webhook delivery failed", "category": "webhook"},
    "integration.connected": {"description": "External integration connected", "category": "integration"},
    "automation.triggered": {"description": "Automation rule triggered", "category": "automation"},
    "evaluation.completed": {"description": "Quality evaluation run completed", "category": "quality"},
    "evaluation.failed": {"description": "Quality evaluation run failed thresholds", "category": "quality"},
    "quality.regression.detected": {"description": "Quality regression detected", "category": "quality"},
    "quality.threshold.violated": {"description": "Quality threshold violated", "category": "quality"},
    "quality.gate.failed": {"description": "Deployment quality gate failed", "category": "quality"},
    "budget.threshold.crossed": {"description": "Budget threshold crossed", "category": "finops"},
    "budget.limit.reached": {"description": "Budget limit reached", "category": "finops"},
    "cost.anomaly.detected": {"description": "Cost anomaly detected", "category": "finops"},
    "forecast.overrun.predicted": {"description": "Forecast predicts budget overrun", "category": "finops"},
    "optimization.recommendation.created": {"description": "Cost optimization recommendation created", "category": "finops"},
}

SAFE_PAYLOAD_KEYS = frozenset({
    "request_id", "model", "provider", "status", "agent_id", "workflow_id",
    "execution_id", "deployment_id", "severity", "recommendation_id", "anomaly_id",
    "integration_id", "automation_id", "error_code", "latency_ms",
    "gate_id", "suite_id", "pass_rate", "run_id",
})


def sanitize_event_data(data: dict | None) -> dict:
    if not data:
        return {}
    return {k: v for k, v in data.items() if k in SAFE_PAYLOAD_KEYS}


class EventCatalog:
    @staticmethod
    def list_events() -> list[dict]:
        return [
            {"type": k, **v}
            for k, v in sorted(EVENT_CATALOG.items())
        ]

    @staticmethod
    def is_valid(event_type: str) -> bool:
        return event_type in EVENT_CATALOG


class EventBus:
    def __init__(self, db: AsyncSession):
        self.db = db

    def envelope(
        self,
        event: PlatformEvent,
        data: dict | None = None,
    ) -> dict:
        return {
            "id": str(event.id),
            "type": event.event_type,
            "organization_id": str(event.organization_id),
            "timestamp": event.created_at.isoformat(),
            "schema_version": event.schema_version,
            "data": sanitize_event_data(data or event.payload_metadata),
        }

    async def emit(
        self,
        *,
        organization_id: uuid.UUID,
        event_type: str,
        data: dict | None = None,
        source: str = "system",
        idempotency_key: str | None = None,
    ) -> PlatformEvent | None:
        if not EventCatalog.is_valid(event_type):
            return None

        if idempotency_key:
            existing = await self.db.execute(
                select(PlatformEvent).where(
                    PlatformEvent.organization_id == organization_id,
                    PlatformEvent.idempotency_key == idempotency_key,
                )
            )
            found = existing.scalar_one_or_none()
            if found:
                return found

        event = PlatformEvent(
            organization_id=organization_id,
            event_type=event_type,
            source=source,
            schema_version=EVENT_SCHEMA_VERSION,
            payload_metadata=sanitize_event_data(data),
            idempotency_key=idempotency_key,
        )
        self.db.add(event)
        await self.db.flush()

        from app.services.platform.dispatch import EventDispatcher

        await EventDispatcher(self.db).dispatch(event, data)
        return event

    async def list_events(
        self,
        organization_id: uuid.UUID,
        *,
        event_type: str | None = None,
        limit: int = 50,
    ) -> list[PlatformEvent]:
        q = (
            select(PlatformEvent)
            .where(PlatformEvent.organization_id == organization_id)
            .order_by(PlatformEvent.created_at.desc())
            .limit(limit)
        )
        if event_type:
            q = q.where(PlatformEvent.event_type == event_type)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_event(self, organization_id: uuid.UUID, event_id: uuid.UUID) -> PlatformEvent | None:
        event = await self.db.get(PlatformEvent, event_id)
        if not event or event.organization_id != organization_id:
            return None
        return event
