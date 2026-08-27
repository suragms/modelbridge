from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.request_log import RequestLog, UsageRecord


class UsageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_request(
        self,
        request_id: str,
        model: str,
        provider: str,
        latency_ms: float,
        status: str,
        error: str | None = None,
        routing_strategy: str | None = None,
        fallback_used: bool = False,
        requested_model: str | None = None,
        routing_policy: str | None = None,
        candidates_count: int | None = None,
        fallback_count: int | None = None,
        user_id: uuid.UUID | None = None,
        api_key_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> RequestLog:
        log = RequestLog(
            request_id=request_id,
            model=model,
            provider=provider,
            latency_ms=latency_ms,
            status=status,
            error=error,
            routing_strategy=routing_strategy,
            fallback_used=fallback_used,
            requested_model=requested_model,
            routing_policy=routing_policy,
            candidates_count=candidates_count,
            fallback_count=fallback_count,
            user_id=user_id,
            api_key_id=api_key_id,
            organization_id=organization_id,
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def log_usage(
        self,
        request_id: str,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> UsageRecord:
        record = UsageRecord(
            request_id=request_id,
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            user_id=user_id,
            organization_id=organization_id,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def get_total_usage(
        self,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> dict:
        query = select(
            func.sum(UsageRecord.input_tokens).label("total_input"),
            func.sum(UsageRecord.output_tokens).label("total_output"),
            func.sum(UsageRecord.total_tokens).label("total_tokens"),
            func.count(UsageRecord.id).label("request_count"),
        )
        if user_id:
            query = query.where(UsageRecord.user_id == user_id)
        if organization_id:
            query = query.where(UsageRecord.organization_id == organization_id)

        result = await self.db.execute(query)
        row = result.one()
        return {
            "total_input_tokens": row.total_input or 0,
            "total_output_tokens": row.total_output or 0,
            "total_tokens": row.total_tokens or 0,
            "request_count": row.request_count or 0,
        }

    async def get_recent_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        user_id: uuid.UUID | None = None,
    ) -> list[RequestLog]:
        query = select(RequestLog).order_by(RequestLog.created_at.desc()).offset(offset).limit(limit)
        if user_id:
            query = query.where(RequestLog.user_id == user_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())
