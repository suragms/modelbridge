from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.schemas.request_log import (
    RequestDetailResponse,
    RequestLogListResponse,
    RequestLogResponse,
)
from app.services.usage import UsageService

router = APIRouter(prefix="/logs", tags=["Request Logs"])


@router.get("/", response_model=RequestLogListResponse)
async def list_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    provider: str | None = Query(None),
    model: str | None = Query(None),
    request_id: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UsageService(db)
    logs, total = await service.search_logs(
        limit=limit,
        offset=offset,
        user_id=user.id,
        status=status,
        provider=provider,
        model=model,
        request_id=request_id,
        start_date=start_date,
        end_date=end_date,
    )

    items = []
    for log in logs:
        usage = await service.get_usage_for_request(log.request_id)
        cost = await service.get_cost_for_request(log.request_id)
        item = RequestLogResponse.model_validate(log)
        item.input_tokens = usage.input_tokens if usage else None
        item.output_tokens = usage.output_tokens if usage else None
        item.total_tokens = usage.total_tokens if usage else None
        item.usage_source = usage.usage_source if usage else None
        item.estimated_total_cost = cost.total_cost if cost else None
        items.append(item)

    return RequestLogListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{request_id}", response_model=RequestDetailResponse)
async def get_log_detail(
    request_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UsageService(db)
    log = await service.get_request_by_id(request_id, user_id=user.id)
    if not log:
        raise HTTPException(status_code=404, detail="Request not found")

    usage = await service.get_usage_for_request(request_id)
    cost = await service.get_cost_for_request(request_id)

    detail = RequestDetailResponse.model_validate(log)
    if usage:
        detail.input_tokens = usage.input_tokens
        detail.output_tokens = usage.output_tokens
        detail.total_tokens = usage.total_tokens
        detail.usage_source = usage.usage_source
    if cost:
        detail.estimated_input_cost = cost.input_cost
        detail.estimated_output_cost = cost.output_cost
        detail.estimated_total_cost = cost.total_cost
        detail.cost_is_estimated = cost.is_estimated
        detail.pricing_source = cost.pricing_source
        detail.currency = cost.currency

    return detail
