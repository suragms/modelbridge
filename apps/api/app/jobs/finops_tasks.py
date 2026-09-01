"""Background jobs for FinOps platform."""

from __future__ import annotations

import structlog
from sqlalchemy import select

from app.db.base import async_session_factory
from app.models.finops import FinopsBudget
from app.models.organization import Organization
from app.services.finops.anomalies import AnomalyService
from app.services.finops.budgets import BudgetService
from app.services.finops.forecasting import ForecastService
from app.services.finops.optimization import OptimizationService
from app.services.finops.overview import OverviewService

logger = structlog.get_logger()


async def run_finops_aggregation(ctx) -> dict:
    aggregated = 0
    async with async_session_factory() as db:
        orgs = await db.execute(select(Organization.id))
        for (org_id,) in orgs.all():
            try:
                count = await OverviewService(db).aggregate_snapshots(org_id)
                aggregated += count
            except Exception as e:
                logger.warning("finops_aggregation_failed", org_id=str(org_id), error=str(e))
        await db.commit()
    return {"snapshots_created": aggregated}


async def run_finops_forecasts(ctx) -> dict:
    generated = 0
    async with async_session_factory() as db:
        orgs = await db.execute(select(Organization.id))
        for (org_id,) in orgs.all():
            try:
                await ForecastService(db).generate(org_id)
                generated += 1
            except Exception as e:
                logger.warning("finops_forecast_failed", org_id=str(org_id), error=str(e))
        await db.commit()
    return {"forecasts_generated": generated}


async def run_finops_anomaly_detection(ctx) -> dict:
    detected = 0
    async with async_session_factory() as db:
        orgs = await db.execute(select(Organization.id))
        for (org_id,) in orgs.all():
            try:
                found = await AnomalyService(db).detect(org_id)
                detected += len(found)
            except Exception as e:
                logger.warning("finops_anomaly_failed", org_id=str(org_id), error=str(e))
        await db.commit()
    return {"anomalies_detected": detected}


async def run_finops_budget_checks(ctx) -> dict:
    checked = 0
    async with async_session_factory() as db:
        result = await db.execute(select(FinopsBudget).where(FinopsBudget.enabled.is_(True)))
        for budget in result.scalars().all():
            try:
                await BudgetService(db).check_thresholds(budget)
                checked += 1
            except Exception as e:
                logger.warning("finops_budget_check_failed", budget_id=str(budget.id), error=str(e))
        await db.commit()
    return {"budgets_checked": checked}


async def run_finops_optimization_analysis(ctx) -> dict:
    analyzed = 0
    async with async_session_factory() as db:
        orgs = await db.execute(select(Organization.id))
        for (org_id,) in orgs.all():
            try:
                recs = await OptimizationService(db).analyze(org_id)
                if recs:
                    analyzed += 1
            except Exception as e:
                logger.warning("finops_optimization_failed", org_id=str(org_id), error=str(e))
        await db.commit()
    return {"organizations_analyzed": analyzed}
