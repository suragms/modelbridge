"""Normalized operational data from existing telemetry sources."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentExecution, ExecutionStatus
from app.models.cloud import UsageMeterEvent
from app.models.provider import Provider, ProviderStatus
from app.models.request_log import (
    FAILED_STATUSES,
    SUCCESS_STATUSES,
    CostRecord,
    RequestLog,
    UsageRecord,
)
from app.services.analytics import AnalyticsService
from app.services.intelligence.data_quality import DataQuality, assess_quality


class OperationalDataFoundation:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.analytics = AnalyticsService(db)

    def default_window(self, days: int = 7) -> tuple[datetime, datetime]:
        end = datetime.now(UTC)
        start = end - timedelta(days=days)
        return start, end

    async def collect_signals(
        self,
        organization_id: uuid.UUID,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> dict[str, Any]:
        start, end = start or self.default_window()[0], end or self.default_window()[1]

        overview = await self.analytics.overview(
            organization_id=organization_id, start_date=start, end_date=end
        )
        providers = await self.analytics.providers(
            organization_id=organization_id, start_date=start, end_date=end
        )
        provider_perf = [
            {
                "provider": p["provider"],
                "request_count": p["total_requests"],
                "success_count": int(p["total_requests"] * p["success_rate"] / 100),
                "failure_count": p.get("error_count", 0),
                "success_rate": p["success_rate"],
                "error_rate": round(100 - p["success_rate"], 2),
                "average_latency_ms": p["average_latency_ms"],
            }
            for p in providers
        ]

        cost_actual = await self._cost_breakdown(organization_id, start, end)
        usage_events = await self._metering_totals(organization_id, start, end)
        agent_stats = await self._agent_stats(organization_id, start, end)
        provider_health = await self._provider_health()

        sample_size = overview.get("total_requests", 0)
        quality = assess_quality(
            sample_size=sample_size,
            min_samples=1,
            time_start=start,
            time_end=end,
        )

        return {
            "window": {"start": start.isoformat(), "end": end.isoformat()},
            "data_quality": quality.to_dict(),
            "overview": overview,
            "providers": providers,
            "provider_performance": provider_perf,
            "costs": cost_actual,
            "usage_events": usage_events,
            "agents": agent_stats,
            "provider_health": provider_health,
        }

    async def _cost_breakdown(
        self, organization_id: uuid.UUID, start: datetime, end: datetime
    ) -> dict:
        actual_q = select(
            func.sum(CostRecord.total_cost).label("total"),
            func.sum(case((CostRecord.is_estimated.is_(False), CostRecord.total_cost), else_=0)).label("actual"),
            func.sum(case((CostRecord.is_estimated.is_(True), CostRecord.total_cost), else_=0)).label("estimated"),
        ).where(
            CostRecord.organization_id == organization_id,
            CostRecord.created_at >= start,
            CostRecord.created_at <= end,
        )
        row = (await self.db.execute(actual_q)).one()
        by_provider = await self.db.execute(
            select(CostRecord.provider, func.sum(CostRecord.total_cost), func.bool_and(CostRecord.is_estimated))
            .where(
                CostRecord.organization_id == organization_id,
                CostRecord.created_at >= start,
                CostRecord.created_at <= end,
            )
            .group_by(CostRecord.provider)
        )
        return {
            "total": float(row.total or 0),
            "actual_cost": float(row.actual or 0),
            "estimated_cost": float(row.estimated or 0),
            "by_provider": [
                {"provider": r[0], "cost": float(r[1] or 0), "is_estimated": bool(r[2])}
                for r in by_provider.all()
            ],
        }

    async def _metering_totals(
        self, organization_id: uuid.UUID, start: datetime, end: datetime
    ) -> dict:
        result = await self.db.execute(
            select(UsageMeterEvent.event_type, func.sum(UsageMeterEvent.quantity))
            .where(
                UsageMeterEvent.organization_id == organization_id,
                UsageMeterEvent.recorded_at >= start,
                UsageMeterEvent.recorded_at <= end,
            )
            .group_by(UsageMeterEvent.event_type)
        )
        return {row[0]: float(row[1]) for row in result.all()}

    async def _agent_stats(
        self, organization_id: uuid.UUID, start: datetime, end: datetime
    ) -> dict:
        total_q = select(func.count()).where(
            AgentExecution.organization_id == organization_id,
            AgentExecution.created_at >= start,
            AgentExecution.created_at <= end,
        )
        failed_q = select(func.count()).where(
            AgentExecution.organization_id == organization_id,
            AgentExecution.status == ExecutionStatus.FAILED,
            AgentExecution.created_at >= start,
            AgentExecution.created_at <= end,
        )
        total = (await self.db.execute(total_q)).scalar() or 0
        failed = (await self.db.execute(failed_q)).scalar() or 0
        return {
            "executions": total,
            "failed": failed,
            "failure_rate": round(failed / total * 100, 2) if total else 0,
        }

    async def _provider_health(self) -> list[dict]:
        result = await self.db.execute(select(Provider))
        return [
            {
                "name": p.name,
                "status": str(p.status),
                "latency_ms": p.last_health_latency_ms,
                "failed_checks": p.failed_health_checks,
            }
            for p in result.scalars().all()
        ]

    async def daily_request_series(
        self, organization_id: uuid.UUID, days: int = 14
    ) -> list[tuple[datetime, float]]:
        end = datetime.now(UTC)
        start = end - timedelta(days=days)
        trunc = func.date_trunc("day", RequestLog.created_at)
        result = await self.db.execute(
            select(trunc.label("day"), func.count(RequestLog.id))
            .where(
                RequestLog.organization_id == organization_id,
                RequestLog.created_at >= start,
                RequestLog.created_at <= end,
            )
            .group_by(trunc)
            .order_by(trunc)
        )
        return [(row.day, float(row[1])) for row in result.all() if row.day]
