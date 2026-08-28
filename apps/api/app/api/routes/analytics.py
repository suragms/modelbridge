from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _parse_range(
    start_date: datetime | None,
    end_date: datetime | None,
) -> tuple[datetime | None, datetime | None]:
    return start_date, end_date


@router.get("/overview")
async def get_overview(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = AnalyticsService(db)
    return await svc.overview(user.id, user.organization_id, start_date, end_date)


@router.get("/summary")
async def get_summary(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Backward-compatible summary endpoint."""
    svc = AnalyticsService(db)
    data = await svc.overview(user.id, user.organization_id, start_date, end_date)
    return {
        "total_requests": data.get("total_requests", 0),
        "total_tokens": data.get("total_tokens", 0),
        "total_input_tokens": data.get("total_input_tokens", 0),
        "total_output_tokens": data.get("total_output_tokens", 0),
        "estimated_total_cost": data.get("estimated_total_cost", 0),
        "success_rate": data.get("success_rate", 0),
        "average_latency_ms": data.get("average_latency_ms", 0),
        "has_data": data.get("has_data", False),
    }


@router.get("/requests")
async def get_requests_analytics(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    provider: str | None = Query(None),
    model: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = AnalyticsService(db)
    return await svc.time_series("requests", user.id, user.organization_id, start_date, end_date)


@router.get("/tokens")
async def get_tokens_analytics(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = AnalyticsService(db)
    return await svc.time_series("tokens", user.id, user.organization_id, start_date, end_date)


@router.get("/cost")
async def get_cost_analytics(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = AnalyticsService(db)
    data = await svc.time_series("cost", user.id, user.organization_id, start_date, end_date)
    data["cost_disclaimer"] = "Estimated cost — may not match provider invoices."
    return data


@router.get("/latency")
async def get_latency_analytics(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = AnalyticsService(db)
    return await svc.time_series("latency", user.id, user.organization_id, start_date, end_date)


@router.get("/errors")
async def get_errors_analytics(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = AnalyticsService(db)
    errors = await svc.errors(user.id, user.organization_id, start_date, end_date, limit)
    ts = await svc.time_series("errors", user.id, user.organization_id, start_date, end_date)
    return {"errors": errors, "time_series": ts}


@router.get("/providers")
async def get_providers_analytics(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = AnalyticsService(db)
    breakdown = await svc.providers(user.id, user.organization_id, start_date, end_date)
    performance = await svc.provider_performance(user.id, start_date, end_date)
    return {"breakdown": breakdown, "performance": performance}


@router.get("/models")
async def get_models_analytics(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = AnalyticsService(db)
    return await svc.models(user.id, user.organization_id, start_date, end_date)


@router.get("/by-model")
async def get_by_model(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = AnalyticsService(db)
    return await svc.models(user.id, user.organization_id)


@router.get("/by-provider")
async def get_by_provider(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = AnalyticsService(db)
    return await svc.providers(user.id, user.organization_id)


@router.get("/api-keys")
async def get_api_key_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = AnalyticsService(db)
    return await svc.api_key_usage(user.id)
