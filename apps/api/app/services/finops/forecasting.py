"""Cost forecasting with documented methodology."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finops import CostType, FinopsBudget, FinopsCostForecast
from app.models.request_log import CostRecord
from app.services.platform.events import EventBus


class ForecastService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate(
        self,
        org_id: uuid.UUID,
        *,
        days: int = 30,
        forecast_days: int = 30,
    ) -> FinopsCostForecast:
        end = datetime.now(UTC)
        start = end - timedelta(days=days)

        daily = await self.db.execute(
            select(
                func.date_trunc("day", CostRecord.created_at).label("day"),
                func.sum(CostRecord.total_cost),
            )
            .where(
                CostRecord.organization_id == org_id,
                CostRecord.created_at >= start,
                CostRecord.created_at <= end,
            )
            .group_by("day")
            .order_by("day")
        )
        rows = daily.all()
        daily_costs = [float(r[1] or 0) for r in rows]

        if len(daily_costs) < 3:
            forecast = FinopsCostForecast(
                organization_id=org_id,
                method="linear_trend",
                historical_period_days=days,
                forecast_amount=0.0,
                cost_type=CostType.UNKNOWN,
                confidence="insufficient_data",
                limitations=(
                    f"Insufficient historical data ({len(daily_costs)} days). "
                    "Forecasts require at least 3 days of cost records. Not a certainty."
                ),
                data_points={"daily_costs": daily_costs, "sample_days": len(daily_costs)},
            )
            self.db.add(forecast)
            await self.db.flush()
            return forecast

        avg_daily = sum(daily_costs) / len(daily_costs)
        if len(daily_costs) >= 2:
            trend = (daily_costs[-1] - daily_costs[0]) / len(daily_costs)
        else:
            trend = 0.0

        projected_daily = max(0, avg_daily + trend)
        forecast_amount = projected_daily * forecast_days

        est_count = await self.db.execute(
            select(func.count()).where(
                CostRecord.organization_id == org_id,
                CostRecord.created_at >= start,
                CostRecord.is_estimated.is_(True),
            )
        )
        has_estimated = (est_count.scalar() or 0) > 0
        cost_type = CostType.ESTIMATED if has_estimated else CostType.ACTUAL
        confidence = "high" if len(daily_costs) >= 14 else ("medium" if len(daily_costs) >= 7 else "low")

        forecast = FinopsCostForecast(
            organization_id=org_id,
            method="linear_trend",
            historical_period_days=days,
            forecast_amount=round(forecast_amount, 6),
            cost_type=cost_type,
            confidence=confidence,
            limitations=(
                "Linear trend extrapolation from historical estimated/actual costs. "
                "Does not account for seasonality, pricing changes, or usage spikes. "
                "Not a billing guarantee."
            ),
            data_points={
                "avg_daily_cost": round(avg_daily, 6),
                "trend_per_day": round(trend, 6),
                "forecast_days": forecast_days,
                "sample_days": len(daily_costs),
            },
        )
        self.db.add(forecast)
        await self.db.flush()
        await self._check_forecast_overrun(org_id, forecast)
        return forecast

    async def list_forecasts(self, org_id: uuid.UUID, limit: int = 10) -> list[FinopsCostForecast]:
        result = await self.db.execute(
            select(FinopsCostForecast)
            .where(FinopsCostForecast.organization_id == org_id)
            .order_by(FinopsCostForecast.generated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _check_forecast_overrun(self, org_id: uuid.UUID, forecast: FinopsCostForecast) -> None:
        if forecast.forecast_amount <= 0 or forecast.confidence == "insufficient_data":
            return
        result = await self.db.execute(
            select(FinopsBudget).where(
                FinopsBudget.organization_id == org_id,
                FinopsBudget.enabled.is_(True),
            )
        )
        for budget in result.scalars().all():
            if forecast.forecast_amount <= budget.amount:
                continue
            await EventBus(self.db).emit(
                organization_id=org_id,
                event_type="forecast.overrun.predicted",
                data={
                    "forecast_amount": forecast.forecast_amount,
                    "budget_amount": budget.amount,
                    "budget_id": str(budget.id),
                    "confidence": forecast.confidence,
                },
                source="finops",
            )
