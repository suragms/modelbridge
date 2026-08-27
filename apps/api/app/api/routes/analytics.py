from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user
from app.db.base import get_db
from app.models.request_log import RequestLog, UsageRecord
from app.models.user import User
from app.services.cost import CostService
from app.services.usage import UsageService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary")
async def get_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    usage_service = UsageService(db)
    cost_service = CostService(db)

    usage = await usage_service.get_total_usage(user_id=user.id)
    total_cost = await cost_service.get_total_cost(user_id=user.id)

    # Success rate
    total_result = await db.execute(
        select(func.count(RequestLog.id)).where(RequestLog.user_id == user.id)
    )
    total_requests = total_result.scalar() or 0

    success_result = await db.execute(
        select(func.count(RequestLog.id)).where(
            RequestLog.user_id == user.id, RequestLog.status == "success"
        )
    )
    success_count = success_result.scalar() or 0

    success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0

    # Average latency
    latency_result = await db.execute(
        select(func.avg(RequestLog.latency_ms)).where(RequestLog.user_id == user.id)
    )
    avg_latency = latency_result.scalar() or 0

    return {
        "total_requests": total_requests,
        "total_tokens": usage["total_tokens"],
        "total_input_tokens": usage["total_input_tokens"],
        "total_output_tokens": usage["total_output_tokens"],
        "estimated_total_cost": round(total_cost, 6),
        "success_rate": round(success_rate, 2),
        "average_latency_ms": round(avg_latency, 2),
    }


@router.get("/by-model")
async def get_by_model(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            UsageRecord.model,
            func.sum(UsageRecord.total_tokens).label("total_tokens"),
            func.count(UsageRecord.id).label("request_count"),
        )
        .where(UsageRecord.user_id == user.id)
        .group_by(UsageRecord.model)
        .order_by(func.count(UsageRecord.id).desc())
        .limit(10)
    )
    rows = result.all()
    return [{"model": row.model, "tokens": row.total_tokens, "requests": row.request_count} for row in rows]


@router.get("/by-provider")
async def get_by_provider(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            UsageRecord.provider,
            func.sum(UsageRecord.total_tokens).label("total_tokens"),
            func.count(UsageRecord.id).label("request_count"),
        )
        .where(UsageRecord.user_id == user.id)
        .group_by(UsageRecord.provider)
        .order_by(func.count(UsageRecord.id).desc())
    )
    rows = result.all()
    return [{"provider": row.provider, "tokens": row.total_tokens, "requests": row.request_count} for row in rows]
