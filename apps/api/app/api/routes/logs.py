from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.schemas.request_log import RequestLogResponse
from app.services.usage import UsageService

router = APIRouter(prefix="/logs", tags=["Request Logs"])


@router.get("/", response_model=list[RequestLogResponse])
async def list_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UsageService(db)
    logs = await service.get_recent_logs(limit=limit, offset=offset, user_id=user.id)
    return [RequestLogResponse.model_validate(log) for log in logs]
