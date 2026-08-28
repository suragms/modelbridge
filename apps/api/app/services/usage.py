from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.request_log import (
    FAILED_STATUSES,
    REQUEST_STATUS_COMPLETED,
    REQUEST_STATUS_FAILED,
    REQUEST_STATUS_ROUTING,
    SUCCESS_STATUSES,
    USAGE_SOURCE_PROVIDER,
    USAGE_SOURCE_UNAVAILABLE,
    CostRecord,
    RequestLog,
    UsageRecord,
)


def generate_request_id() -> str:
    return f"req_{uuid.uuid4().hex}"


def is_success_status(status: str) -> bool:
    return status in SUCCESS_STATUSES


class UsageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_request(
        self,
        request_id: str,
        requested_model: str,
        user_id: uuid.UUID | None = None,
        api_key_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        routing_policy: str | None = None,
        routing_strategy: str | None = None,
        request_type: str = "chat",
        required_capabilities: str | None = None,
        input_count: int | None = None,
    ) -> RequestLog:
        log = RequestLog(
            request_id=request_id,
            model=requested_model,
            selected_model=requested_model,
            provider="pending",
            latency_ms=0,
            status=REQUEST_STATUS_ROUTING,
            requested_model=requested_model,
            routing_policy=routing_policy,
            routing_strategy=routing_strategy,
            request_type=request_type,
            required_capabilities=required_capabilities,
            input_count=input_count,
            user_id=user_id,
            api_key_id=api_key_id,
            organization_id=organization_id,
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def update_status(self, request_id: str, status: str) -> None:
        result = await self.db.execute(
            select(RequestLog).where(RequestLog.request_id == request_id)
        )
        log = result.scalar_one_or_none()
        if log:
            log.status = status

    async def complete_request(
        self,
        request_id: str,
        model: str,
        provider: str,
        latency_ms: float,
        status: str = REQUEST_STATUS_COMPLETED,
        error: str | None = None,
        error_code: str | None = None,
        error_type: str | None = None,
        routing_strategy: str | None = None,
        fallback_used: bool = False,
        requested_model: str | None = None,
        routing_policy: str | None = None,
        candidates_count: int | None = None,
        fallback_count: int | None = None,
        provider_latency_ms: float | None = None,
        user_id: uuid.UUID | None = None,
        api_key_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        request_type: str | None = None,
        required_capabilities: str | None = None,
        input_count: int | None = None,
    ) -> RequestLog:
        result = await self.db.execute(
            select(RequestLog).where(RequestLog.request_id == request_id)
        )
        log = result.scalar_one_or_none()

        if log:
            log.model = model
            log.selected_model = model
            log.provider = provider
            log.latency_ms = latency_ms
            log.status = status
            log.error = error
            log.error_code = error_code
            log.error_type = error_type
            log.routing_strategy = routing_strategy
            log.fallback_used = fallback_used
            log.requested_model = requested_model
            log.routing_policy = routing_policy
            log.candidates_count = candidates_count
            log.fallback_count = fallback_count
            log.provider_latency_ms = provider_latency_ms
            log.completed_at = datetime.now(UTC)
            if api_key_id:
                log.api_key_id = api_key_id
            if request_type:
                log.request_type = request_type
            if required_capabilities is not None:
                log.required_capabilities = required_capabilities
            if input_count is not None:
                log.input_count = input_count
        else:
            log = RequestLog(
                request_id=request_id,
                model=model,
                selected_model=model,
                provider=provider,
                latency_ms=latency_ms,
                status=status,
                error=error,
                error_code=error_code,
                error_type=error_type,
                routing_strategy=routing_strategy,
                fallback_used=fallback_used,
                requested_model=requested_model,
                routing_policy=routing_policy,
                candidates_count=candidates_count,
                fallback_count=fallback_count,
                provider_latency_ms=provider_latency_ms,
                completed_at=datetime.now(UTC),
                user_id=user_id,
                api_key_id=api_key_id,
                organization_id=organization_id,
                request_type=request_type or "chat",
                required_capabilities=required_capabilities,
                input_count=input_count,
            )
            self.db.add(log)

        await self.db.flush()
        return log

    async def log_request(self, **kwargs) -> RequestLog:
        """Backward-compatible single-shot log (creates completed record)."""
        status = kwargs.pop("status", REQUEST_STATUS_COMPLETED)
        if status == "success":
            status = REQUEST_STATUS_COMPLETED
        elif status == "error":
            status = REQUEST_STATUS_FAILED

        model = kwargs.get("model", "unknown")
        return await self.complete_request(
            request_id=kwargs["request_id"],
            model=model,
            provider=kwargs.get("provider", "unknown"),
            latency_ms=kwargs.get("latency_ms", 0),
            status=status,
            error=kwargs.get("error"),
            routing_strategy=kwargs.get("routing_strategy"),
            fallback_used=kwargs.get("fallback_used", False),
            requested_model=kwargs.get("requested_model"),
            routing_policy=kwargs.get("routing_policy"),
            candidates_count=kwargs.get("candidates_count"),
            fallback_count=kwargs.get("fallback_count"),
            user_id=kwargs.get("user_id"),
            api_key_id=kwargs.get("api_key_id"),
            organization_id=kwargs.get("organization_id"),
        )

    async def log_usage(
        self,
        request_id: str,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        usage_source: str = USAGE_SOURCE_UNAVAILABLE,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> UsageRecord:
        if usage_source == USAGE_SOURCE_UNAVAILABLE and (input_tokens > 0 or output_tokens > 0):
            usage_source = USAGE_SOURCE_PROVIDER

        record = UsageRecord(
            request_id=request_id,
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            usage_source=usage_source,
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
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        query = select(
            func.sum(UsageRecord.input_tokens).label("total_input"),
            func.sum(UsageRecord.output_tokens).label("total_output"),
            func.sum(UsageRecord.total_tokens).label("total_tokens"),
            func.count(UsageRecord.id).label("request_count"),
        )
        conditions = self._scope_conditions(UsageRecord, user_id, organization_id, start_date, end_date)
        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        row = result.one()
        return {
            "total_input_tokens": row.total_input or 0,
            "total_output_tokens": row.total_output or 0,
            "total_tokens": row.total_tokens or 0,
            "request_count": row.request_count or 0,
        }

    async def get_request_by_id(
        self, request_id: str, user_id: uuid.UUID | None = None
    ) -> RequestLog | None:
        query = select(RequestLog).where(RequestLog.request_id == request_id)
        if user_id:
            query = query.where(RequestLog.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_usage_for_request(self, request_id: str) -> UsageRecord | None:
        result = await self.db.execute(
            select(UsageRecord).where(UsageRecord.request_id == request_id)
        )
        return result.scalar_one_or_none()

    async def get_cost_for_request(self, request_id: str) -> CostRecord | None:
        result = await self.db.execute(
            select(CostRecord).where(CostRecord.request_id == request_id)
        )
        return result.scalar_one_or_none()

    async def search_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        status: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        request_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[list[RequestLog], int]:
        conditions = self._scope_conditions(
            RequestLog, user_id, organization_id, start_date, end_date
        )
        if status:
            if status.upper() == REQUEST_STATUS_COMPLETED:
                conditions.append(RequestLog.status.in_(list(SUCCESS_STATUSES)))
            elif status.upper() == REQUEST_STATUS_FAILED:
                conditions.append(RequestLog.status.in_(list(FAILED_STATUSES)))
            else:
                conditions.append(RequestLog.status == status.upper())
        if provider:
            conditions.append(RequestLog.provider.ilike(f"%{provider}%"))
        if model:
            conditions.append(
                or_(
                    RequestLog.model.ilike(f"%{model}%"),
                    RequestLog.requested_model.ilike(f"%{model}%"),
                )
            )
        if request_id:
            conditions.append(RequestLog.request_id.ilike(f"%{request_id}%"))

        count_query = select(func.count(RequestLog.id))
        data_query = select(RequestLog).order_by(RequestLog.created_at.desc())
        if conditions:
            where = and_(*conditions)
            count_query = count_query.where(where)
            data_query = data_query.where(where)

        total = (await self.db.execute(count_query)).scalar() or 0
        result = await self.db.execute(data_query.offset(offset).limit(limit))
        return list(result.scalars().all()), total

    async def get_recent_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        user_id: uuid.UUID | None = None,
    ) -> list[RequestLog]:
        logs, _ = await self.search_logs(limit=limit, offset=offset, user_id=user_id)
        return logs

    @staticmethod
    def _scope_conditions(
        model_cls,
        user_id: uuid.UUID | None,
        organization_id: uuid.UUID | None,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> list:
        conditions = []
        if user_id:
            conditions.append(model_cls.user_id == user_id)
        if organization_id:
            conditions.append(model_cls.organization_id == organization_id)
        if start_date:
            conditions.append(model_cls.created_at >= start_date)
        if end_date:
            conditions.append(model_cls.created_at <= end_date)
        return conditions
