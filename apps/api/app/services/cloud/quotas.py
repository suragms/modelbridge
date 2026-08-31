"""Quota enforcement."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud import Quota, QuotaPeriod, QuotaResource, UsageEventType, UsageMeterEvent


class QuotaExceeded(Exception):
    def __init__(self, resource: str, limit: float, current: float):
        self.resource = resource
        self.limit = limit
        self.current = current
        super().__init__(f"Quota exceeded for {resource}: {current}/{limit}")


PERIOD_DELTA = {
    QuotaPeriod.HOURLY: timedelta(hours=1),
    QuotaPeriod.DAILY: timedelta(days=1),
    QuotaPeriod.MONTHLY: timedelta(days=30),
}

RESOURCE_EVENT_MAP = {
    QuotaResource.REQUESTS: UsageEventType.REQUEST,
    QuotaResource.TOKENS: UsageEventType.TOKENS,
    QuotaResource.AGENT_EXECUTIONS: UsageEventType.AGENT_EXECUTION,
}


class QuotaService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_quotas(self, organization_id: uuid.UUID) -> list[Quota]:
        result = await self.db.execute(
            select(Quota).where(Quota.organization_id == organization_id).order_by(Quota.resource)
        )
        return list(result.scalars().all())

    async def upsert(
        self,
        *,
        organization_id: uuid.UUID,
        resource: str,
        period: str,
        limit_value: float,
        is_enabled: bool = True,
    ) -> Quota:
        existing = await self.db.execute(
            select(Quota).where(
                Quota.organization_id == organization_id,
                Quota.resource == resource,
                Quota.period == period,
            )
        )
        quota = existing.scalar_one_or_none()
        if quota:
            quota.limit_value = limit_value
            quota.is_enabled = is_enabled
        else:
            quota = Quota(
                organization_id=organization_id,
                resource=resource,
                period=period,
                limit_value=limit_value,
                is_enabled=is_enabled,
            )
            self.db.add(quota)
        await self.db.flush()
        return quota

    async def usage_in_period(self, organization_id: uuid.UUID, quota: Quota) -> float:
        delta = PERIOD_DELTA.get(quota.period, timedelta(days=1))
        since = datetime.now(UTC) - delta
        event_type = RESOURCE_EVENT_MAP.get(quota.resource, quota.resource)
        result = await self.db.execute(
            select(func.coalesce(func.sum(UsageMeterEvent.quantity), 0)).where(
                UsageMeterEvent.organization_id == organization_id,
                UsageMeterEvent.event_type == event_type,
                UsageMeterEvent.recorded_at >= since,
            )
        )
        return float(result.scalar_one())

    async def check(self, organization_id: uuid.UUID, resource: str, *, increment: float = 0) -> dict:
        """Check quota; fail safely by allowing when no quota configured."""
        result = await self.db.execute(
            select(Quota).where(
                Quota.organization_id == organization_id,
                Quota.resource == resource,
                Quota.is_enabled == True,  # noqa: E712
            )
        )
        quota = result.scalar_one_or_none()
        if not quota:
            return {"allowed": True, "resource": resource, "limit": None, "current": 0}

        current = await self.usage_in_period(organization_id, quota)
        projected = current + increment
        allowed = projected <= quota.limit_value
        return {
            "allowed": allowed,
            "resource": resource,
            "limit": quota.limit_value,
            "current": current,
            "period": quota.period,
        }

    async def enforce(self, organization_id: uuid.UUID, resource: str, *, increment: float = 1) -> None:
        status = await self.check(organization_id, resource, increment=increment)
        if not status["allowed"]:
            raise QuotaExceeded(resource, status["limit"], status["current"] + increment)
