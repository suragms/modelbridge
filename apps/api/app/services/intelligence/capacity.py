"""Capacity intelligence and forecasting."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import AutomationLevel, RecommendationCategory
from app.models.job_run import JobRun
from app.models.request_log import RequestLog
from app.services.intelligence.data_quality import assess_quality
from app.services.intelligence.foundation import OperationalDataFoundation
from app.services.intelligence.forecasting import ForecastingService
from app.services.intelligence.recommendations import RecommendationService


class CapacityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.foundation = OperationalDataFoundation(db)
        self.forecasting = ForecastingService(db)
        self.recommendations = RecommendationService(db)

    async def analyze(self, organization_id: uuid.UUID, *, days: int = 14) -> dict:
        start, end = self.foundation.default_window(days)
        series = await self.foundation.daily_request_series(organization_id, days=days)
        quality = assess_quality(sample_size=len(series), min_samples=7, time_start=start, time_end=end)

        current_load = series[-1][1] if series else 0
        avg_load = sum(v for _, v in series) / len(series) if series else 0

        job_failures = await self.db.execute(
            select(func.count()).where(
                JobRun.status == "failed",
                JobRun.created_at >= start,
            )
        )
        failed_jobs = job_failures.scalar() or 0

        forecast = await self.forecasting.forecast_requests(organization_id, days=days)
        risks = []
        if forecast.get("status") == "ok":
            trend = forecast.get("supporting_data", {}).get("trend_per_day", 0)
            if trend > 0 and avg_load > 0 and current_load > avg_load * 1.2:
                risks.append({
                    "type": "growing_load",
                    "message": "Request volume is trending upward above recent average.",
                    "evidence": {"current": current_load, "average": avg_load, "trend_per_day": trend},
                })

        recs = []
        if risks and quality.status != "insufficient_data":
            rec = await self.recommendations.create(
                organization_id=organization_id,
                category=RecommendationCategory.CAPACITY,
                title="Capacity review recommended",
                description=(
                    "Additional workers may be required if the current request growth trend continues."
                ),
                evidence={"risks": risks, "forecast": forecast.get("forecast_value")},
                suggested_action="Review worker replicas and queue depth monitoring.",
                confidence=forecast.get("confidence", 0.5),
                automation_level=AutomationLevel.RECOMMEND,
            )
            recs.append(rec)

        health = "healthy"
        if current_load > avg_load * 1.5:
            health = "watch"
        if failed_jobs > 10:
            health = "at_risk"

        return {
            "status": "ok" if quality.status != "insufficient_data" else "insufficient_data",
            "data_quality": quality.to_dict(),
            "current_daily_requests": current_load,
            "average_daily_requests": round(avg_load, 1),
            "failed_background_jobs": failed_jobs,
            "capacity_health": health,
            "risks": risks,
            "forecast": forecast,
            "recommendations_created": len(recs),
            "disclaimer": "Capacity forecasts are indicative, not guarantees.",
        }
