"""Estimated cost budget enforcement and alert records."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget_alert import BudgetAlert
from app.models.request_log import CostRecord, RequestLog


async def _monthly_spend(
    db: AsyncSession,
    *,
    organization_id,
    api_key_id=None,
) -> float:
    month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    q = (
        select(func.coalesce(func.sum(CostRecord.total_cost), 0.0))
        .join(RequestLog, RequestLog.request_id == CostRecord.request_id)
        .where(RequestLog.created_at >= month_start)
    )
    if api_key_id:
        q = q.where(RequestLog.api_key_id == api_key_id)
    elif organization_id:
        q = q.where(RequestLog.organization_id == organization_id)
    result = await db.execute(q)
    return float(result.scalar_one() or 0.0)


async def _maybe_create_alert(
    db: AsyncSession,
    *,
    organization_id,
    api_key_id,
    budget_usd: float,
    spend: float,
    warning_percent: int,
    hard_limit_percent: int,
) -> None:
    if budget_usd <= 0:
        return
    pct = (spend / budget_usd) * 100
    thresholds = [
        (hard_limit_percent, "budget_limit_reached", "Budget hard limit reached"),
        (90, "budget_90", "90% of estimated monthly budget used"),
        (warning_percent, "budget_warning", f"{warning_percent}% of estimated monthly budget used"),
    ]
    for threshold, alert_type, msg in thresholds:
        if pct < threshold:
            continue
        existing = await db.execute(
            select(BudgetAlert).where(
                BudgetAlert.organization_id == organization_id,
                BudgetAlert.api_key_id == api_key_id,
                BudgetAlert.alert_type == alert_type,
                BudgetAlert.created_at >= datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            )
        )
        if existing.scalar_one_or_none():
            continue
        db.add(
            BudgetAlert(
                organization_id=organization_id,
                api_key_id=api_key_id,
                alert_type=alert_type,
                threshold_percent=threshold,
                estimated_spend_usd=spend,
                budget_usd=budget_usd,
                message=(
                    f"{msg}. Estimated spend: ${spend:.4f} of ${budget_usd:.2f} budget. "
                    "Based on estimated cost data — not exact provider billing."
                ),
            )
        )
        await db.flush()
        break


async def check_budget(
    db: AsyncSession,
    *,
    organization_id,
    api_key_id=None,
    org_budget_usd: float | None,
    key_budget_usd: float | None,
    warning_percent: int = 80,
    hard_limit_percent: int = 100,
) -> None:
    """Reject requests when estimated spend exceeds hard limit."""
    if key_budget_usd and key_budget_usd > 0:
        spend = await _monthly_spend(db, organization_id=organization_id, api_key_id=api_key_id)
        await _maybe_create_alert(
            db,
            organization_id=organization_id,
            api_key_id=api_key_id,
            budget_usd=key_budget_usd,
            spend=spend,
            warning_percent=warning_percent,
            hard_limit_percent=hard_limit_percent,
        )
        hard = key_budget_usd * (hard_limit_percent / 100.0)
        if spend >= hard:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "BUDGET_EXCEEDED",
                    "message": (
                        "API key estimated monthly budget exceeded. "
                        "Based on estimated cost data — not exact provider billing."
                    ),
                    "type": "budget_error",
                },
            )

    if org_budget_usd and org_budget_usd > 0:
        spend = await _monthly_spend(db, organization_id=organization_id)
        await _maybe_create_alert(
            db,
            organization_id=organization_id,
            api_key_id=None,
            budget_usd=org_budget_usd,
            spend=spend,
            warning_percent=warning_percent,
            hard_limit_percent=hard_limit_percent,
        )
        hard = org_budget_usd * (hard_limit_percent / 100.0)
        if spend >= hard:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "BUDGET_EXCEEDED",
                    "message": (
                        "Organization estimated monthly budget exceeded. "
                        "Based on estimated cost data — not exact provider billing."
                    ),
                    "type": "budget_error",
                },
            )


async def get_monthly_spend(
    db: AsyncSession,
    organization_id,
    api_key_id=None,
) -> float:
    return await _monthly_spend(db, organization_id=organization_id, api_key_id=api_key_id)
