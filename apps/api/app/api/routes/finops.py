"""AI FinOps & Cost Intelligence APIs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.org_context import OrgContext
from app.auth.rbac import Permission, require_permission
from app.db.base import get_db
from app.models.finops import FinopsBudget, FinopsCostAnomaly, FinopsOptimizationRecommendation
from app.schemas.finops import BudgetCreate, BudgetResponse, FinopsOverviewResponse, PricingVersionCreate
from app.services.finops.anomalies import AnomalyService
from app.services.finops.budgets import BudgetService
from app.services.finops.chargeback import ChargebackService
from app.services.finops.engine import CostEngine
from app.services.finops.forecasting import ForecastService
from app.services.finops.optimization import OptimizationService
from app.services.finops.overview import OverviewService

router = APIRouter(prefix="/finops", tags=["FinOps"])


@router.get("/overview", response_model=FinopsOverviewResponse)
async def finops_overview(
    ctx: OrgContext = Depends(require_permission(Permission.FINOPS_READ)),
    db: AsyncSession = Depends(get_db),
):
    overview = await OverviewService(db).overview(ctx.organization_id)
    budgets = await BudgetService(db).list_budgets(ctx.organization_id)
    anomalies = await AnomalyService(db).list_anomalies(ctx.organization_id, limit=5)
    open_anomalies = sum(1 for a in anomalies if a.status == "open")
    recs = await OptimizationService(db).list_recommendations(ctx.organization_id)
    forecasts = await ForecastService(db).list_forecasts(ctx.organization_id, limit=1)
    forecast_amount = forecasts[0].forecast_amount if forecasts else None

    return FinopsOverviewResponse(
        current_spend=overview["current_spend"],
        cost_type=overview["cost_type"],
        request_count=overview["request_count"],
        period=overview["period"],
        top_cost_drivers=overview["top_cost_drivers"],
        open_anomalies=open_anomalies,
        active_budgets=len(budgets),
        forecast_amount=forecast_amount,
        optimization_count=len([r for r in recs if r.status == "open"]),
    )


@router.get("/costs")
async def explore_costs(
    days: int = Query(30, ge=1, le=365),
    provider: str | None = None,
    model: str | None = None,
    breakdown: str = "provider",
    ctx: OrgContext = Depends(require_permission(Permission.FINOPS_READ)),
    db: AsyncSession = Depends(get_db),
):
    return await OverviewService(db).explore(
        ctx.organization_id,
        days=days,
        provider=provider,
        model=model,
        breakdown=breakdown,
    )


@router.get("/budgets", response_model=list[BudgetResponse])
async def list_budgets(
    ctx: OrgContext = Depends(require_permission(Permission.FINOPS_READ)),
    db: AsyncSession = Depends(get_db),
):
    budgets = await BudgetService(db).list_budgets(ctx.organization_id)
    return [
        BudgetResponse(
            id=b.id, name=b.name, scope=b.scope, amount=b.amount,
            currency=b.currency, period=b.period, enabled=b.enabled, created_at=b.created_at,
        )
        for b in budgets
    ]


@router.post("/budgets", status_code=status.HTTP_201_CREATED)
async def create_budget(
    payload: BudgetCreate,
    ctx: OrgContext = Depends(require_permission(Permission.FINOPS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    budget = await BudgetService(db).create(
        org_id=ctx.organization_id,
        name=payload.name,
        amount=payload.amount,
        scope=payload.scope,
        scope_id=payload.scope_id,
        currency=payload.currency,
        period=payload.period,
        thresholds=payload.thresholds,
        enforcement_action=payload.enforcement_action,
        user_id=ctx.user.id,
    )
    await db.commit()
    return {"id": str(budget.id)}


@router.get("/budgets/{budget_id}/status")
async def budget_status(
    budget_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.FINOPS_READ)),
    db: AsyncSession = Depends(get_db),
):
    budget = await BudgetService(db).get_budget(ctx.organization_id, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    await BudgetService(db).check_thresholds(budget)
    await db.commit()
    return await BudgetService(db).budget_status(budget)


@router.get("/forecast")
async def get_forecast(
    days: int = Query(30, ge=7, le=90),
    ctx: OrgContext = Depends(require_permission(Permission.FINOPS_READ)),
    db: AsyncSession = Depends(get_db),
):
    forecast = await ForecastService(db).generate(ctx.organization_id, days=days)
    await db.commit()
    return {
        "id": str(forecast.id),
        "forecast_amount": forecast.forecast_amount,
        "method": forecast.method,
        "cost_type": forecast.cost_type,
        "confidence": forecast.confidence,
        "limitations": forecast.limitations,
        "historical_period_days": forecast.historical_period_days,
        "data_points": forecast.data_points,
        "generated_at": forecast.generated_at.isoformat(),
    }


@router.post("/forecast/generate")
async def generate_forecast(
    days: int = Query(30, ge=7, le=90),
    ctx: OrgContext = Depends(require_permission(Permission.FINOPS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    forecast = await ForecastService(db).generate(ctx.organization_id, days=days)
    await db.commit()
    return {"id": str(forecast.id), "forecast_amount": forecast.forecast_amount}


@router.get("/anomalies")
async def list_anomalies(
    ctx: OrgContext = Depends(require_permission(Permission.FINOPS_READ)),
    db: AsyncSession = Depends(get_db),
):
    items = await AnomalyService(db).list_anomalies(ctx.organization_id)
    return [
        {
            "id": str(a.id),
            "type": a.anomaly_type,
            "status": a.status,
            "affected_scope": a.affected_scope,
            "expected_range": a.expected_range,
            "observed_value": a.observed_value,
            "evidence": a.evidence,
            "detected_at": a.detected_at.isoformat(),
        }
        for a in items
    ]


@router.post("/anomalies/detect")
async def detect_anomalies(
    ctx: OrgContext = Depends(require_permission(Permission.FINOPS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    found = await AnomalyService(db).detect(ctx.organization_id)
    await db.commit()
    return {"detected": len(found)}


@router.get("/recommendations")
async def list_recommendations(
    ctx: OrgContext = Depends(require_permission(Permission.FINOPS_READ)),
    db: AsyncSession = Depends(get_db),
):
    items = await OptimizationService(db).list_recommendations(ctx.organization_id)
    return [
        {
            "id": str(r.id),
            "category": r.category,
            "title": r.title,
            "description": r.description,
            "evidence": r.evidence,
            "projected_savings": r.projected_savings,
            "savings_status": r.savings_status,
            "assumptions": r.assumptions,
            "confidence": r.confidence,
            "risk": r.risk,
            "status": r.status,
        }
        for r in items
    ]


@router.post("/recommendations/analyze")
async def analyze_optimizations(
    ctx: OrgContext = Depends(require_permission(Permission.FINOPS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    recs = await OptimizationService(db).analyze(ctx.organization_id)
    await db.commit()
    return {"created": len(recs)}


@router.post("/recommendations/{rec_id}/approve")
async def approve_recommendation(
    rec_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.FINOPS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    rec = await OptimizationService(db).approve(ctx.organization_id, rec_id, ctx.user.id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    await db.commit()
    return {"id": str(rec.id), "status": rec.status}


@router.get("/models/comparison")
async def model_cost_comparison(
    days: int = Query(30, ge=1, le=365),
    ctx: OrgContext = Depends(require_permission(Permission.FINOPS_READ)),
    db: AsyncSession = Depends(get_db),
):
    return await OverviewService(db).model_comparison(ctx.organization_id, days=days)


@router.post("/pricing", status_code=status.HTTP_201_CREATED)
async def create_pricing_version(
    payload: PricingVersionCreate,
    ctx: OrgContext = Depends(require_permission(Permission.FINOPS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    pricing = await CostEngine(db).create_pricing_version(
        org_id=ctx.organization_id,
        provider=payload.provider,
        model=payload.model,
        input_price_per_million=payload.input_price_per_million,
        output_price_per_million=payload.output_price_per_million,
        currency=payload.currency,
        user_id=ctx.user.id,
    )
    await db.commit()
    return {"id": str(pricing.id), "version": pricing.version}


@router.get("/reports/showback")
async def showback_report(
    days: int = Query(30, ge=1, le=365),
    ctx: OrgContext = Depends(require_permission(Permission.FINOPS_READ)),
    db: AsyncSession = Depends(get_db),
):
    end = datetime.now(UTC)
    start = end - timedelta(days=days)
    report = await ChargebackService(db).generate_showback(
        ctx.organization_id, period_start=start, period_end=end, user_id=ctx.user.id
    )
    await db.commit()
    return {
        "id": str(report.id),
        "total_cost": report.total_cost,
        "cost_type": report.cost_type,
        "breakdown": report.breakdown,
        "limitations": "Showback based on attributed cost records; accounting integration not included",
    }


@router.get("/reports")
async def list_reports(
    ctx: OrgContext = Depends(require_permission(Permission.FINOPS_READ)),
    db: AsyncSession = Depends(get_db),
):
    reports = await ChargebackService(db).list_reports(ctx.organization_id)
    return [
        {
            "id": str(r.id),
            "type": r.report_type,
            "total_cost": r.total_cost,
            "cost_type": r.cost_type,
            "generated_at": r.generated_at.isoformat(),
        }
        for r in reports
    ]
