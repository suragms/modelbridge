"""Forecasting with simple trend analysis and honest confidence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import IntelligenceForecast
from app.services.intelligence.data_quality import MIN_SAMPLES_FORECAST, assess_quality
from app.services.intelligence.foundation import OperationalDataFoundation


class ForecastingService:
    METHOD = "linear_trend"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.foundation = OperationalDataFoundation(db)

    async def forecast_requests(
        self, organization_id: uuid.UUID, *, days: int = 14, horizon: int = 7
    ) -> dict:
        series = await self.foundation.daily_request_series(organization_id, days=days)
        quality = assess_quality(
            sample_size=len(series),
            min_samples=MIN_SAMPLES_FORECAST,
        )

        if quality.status == "insufficient_data":
            return {
                "status": "insufficient_data",
                "forecast_type": "requests",
                "data_quality": quality.to_dict(),
                "message": f"Need at least {MIN_SAMPLES_FORECAST} days of data for forecasting.",
            }

        values = [v for _, v in series]
        forecast_value, trend = self._linear_forecast(values, horizon)
        confidence = quality.confidence * (0.9 if len(values) >= 14 else 0.7)

        record = IntelligenceForecast(
            organization_id=organization_id,
            forecast_type="requests",
            historical_window_days=days,
            method=self.METHOD,
            horizon_days=horizon,
            forecast_value=forecast_value,
            confidence=confidence,
            data_quality=quality.status,
            supporting_data={
                "daily_values": values[-7:],
                "trend_per_day": trend,
                "historical_window_days": days,
            },
        )
        self.db.add(record)
        await self.db.flush()

        return {
            "status": "ok",
            "forecast_type": "requests",
            "forecast_value": round(forecast_value, 1),
            "horizon_days": horizon,
            "method": self.METHOD,
            "confidence": round(confidence, 3),
            "data_quality": quality.to_dict(),
            "supporting_data": record.supporting_data,
            "disclaimer": "Forecasts are trend-based estimates, not guarantees.",
        }

    async def forecast_cost(
        self, organization_id: uuid.UUID, *, days: int = 14, horizon: int = 7
    ) -> dict:
        from app.models.request_log import CostRecord
        from sqlalchemy import func, select

        end = datetime.now(UTC)
        start = end - timedelta(days=days)
        trunc = func.date_trunc("day", CostRecord.created_at)
        result = await self.db.execute(
            select(trunc, func.sum(CostRecord.total_cost))
            .where(
                CostRecord.organization_id == organization_id,
                CostRecord.created_at >= start,
                CostRecord.created_at <= end,
            )
            .group_by(trunc)
            .order_by(trunc)
        )
        series = [(r[0], float(r[1] or 0)) for r in result.all() if r[0]]
        quality = assess_quality(sample_size=len(series), min_samples=MIN_SAMPLES_FORECAST)

        if quality.status == "insufficient_data":
            return {
                "status": "insufficient_data",
                "forecast_type": "estimated_cost",
                "data_quality": quality.to_dict(),
            }

        values = [v for _, v in series]
        forecast_value, trend = self._linear_forecast(values, horizon)
        confidence = quality.confidence * 0.75

        record = IntelligenceForecast(
            organization_id=organization_id,
            forecast_type="estimated_cost",
            historical_window_days=days,
            method=self.METHOD,
            horizon_days=horizon,
            forecast_value=forecast_value,
            confidence=confidence,
            data_quality=quality.status,
            supporting_data={"daily_costs": values[-7:], "trend_per_day": trend},
        )
        self.db.add(record)
        await self.db.flush()

        return {
            "status": "ok",
            "forecast_type": "estimated_cost",
            "forecast_value": round(forecast_value, 6),
            "horizon_days": horizon,
            "method": self.METHOD,
            "confidence": round(confidence, 3),
            "data_quality": quality.to_dict(),
            "cost_disclaimer": "Estimated cost forecast — not a billing commitment.",
        }

    def _linear_forecast(self, values: list[float], horizon: int) -> tuple[float, float]:
        if not values:
            return 0.0, 0.0
        if len(values) == 1:
            return values[0] * horizon, 0.0
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        num = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        den = sum((i - x_mean) ** 2 for i in range(n)) or 1
        slope = num / den
        next_val = values[-1] + slope * horizon
        return max(0, next_val), round(slope, 4)
