"""Cost anomaly detection with evidence."""

from __future__ import annotations

import statistics
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finops import AnomalyStatus, FinopsCostAnomaly
from app.models.request_log import CostRecord
from app.services.metrics import record_finops_anomaly
from app.services.platform.events import EventBus


class AnomalyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect(self, org_id: uuid.UUID, *, lookback_days: int = 14) -> list[FinopsCostAnomaly]:
        end = datetime.now(UTC)
        start = end - timedelta(days=lookback_days)
        today_start = end.replace(hour=0, minute=0, second=0, microsecond=0)

        daily = await self.db.execute(
            select(
                func.date_trunc("day", CostRecord.created_at).label("day"),
                func.sum(CostRecord.total_cost),
                func.count(),
            )
            .where(
                CostRecord.organization_id == org_id,
                CostRecord.created_at >= start,
                CostRecord.created_at < today_start,
            )
            .group_by("day")
        )
        history = [float(r[1] or 0) for r in daily.all()]

        today_result = await self.db.execute(
            select(func.coalesce(func.sum(CostRecord.total_cost), 0.0), func.count()).where(
                CostRecord.organization_id == org_id,
                CostRecord.created_at >= today_start,
            )
        )
        today_row = today_result.one()
        today_cost = float(today_row[0] or 0)
        today_count = int(today_row[1] or 0)

        anomalies: list[FinopsCostAnomaly] = []
        if len(history) < 3:
            return anomalies

        mean = statistics.mean(history)
        stdev = statistics.stdev(history) if len(history) > 1 else 0
        upper = mean + 2 * stdev if stdev > 0 else mean * 2

        if today_cost > upper and today_cost > 0:
            anomaly = FinopsCostAnomaly(
                organization_id=org_id,
                anomaly_type="cost_spike",
                status=AnomalyStatus.OPEN,
                affected_scope="organization",
                expected_range={"min": 0, "max": round(upper, 6), "mean": round(mean, 6)},
                observed_value=today_cost,
                evidence={
                    "method": "z_score_2sigma",
                    "historical_days": len(history),
                    "today_request_count": today_count,
                    "stdev": round(stdev, 6),
                },
            )
            self.db.add(anomaly)
            anomalies.append(anomaly)
            record_finops_anomaly(status="detected")
            await EventBus(self.db).emit(
                organization_id=org_id,
                event_type="cost.anomaly.detected",
                data={"status": "open", "execution_id": str(anomaly.id)},
                source="finops",
            )

        await self.db.flush()
        return anomalies

    async def list_anomalies(self, org_id: uuid.UUID, limit: int = 50) -> list[FinopsCostAnomaly]:
        result = await self.db.execute(
            select(FinopsCostAnomaly)
            .where(FinopsCostAnomaly.organization_id == org_id)
            .order_by(FinopsCostAnomaly.detected_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
