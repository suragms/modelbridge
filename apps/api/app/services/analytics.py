from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.request_log import (
    FAILED_STATUSES,
    SUCCESS_STATUSES,
    CostRecord,
    RequestLog,
    UsageRecord,
)
from app.services.cost import CostService
from app.services.usage import UsageService


def _parse_dates(
    start_date: datetime | None, end_date: datetime | None
) -> tuple[datetime | None, datetime | None]:
    return start_date, end_date


def _success_condition():
    return RequestLog.status.in_(list(SUCCESS_STATUSES))


def _failed_condition():
    return RequestLog.status.in_(list(FAILED_STATUSES))


def _choose_bucket(start: datetime | None, end: datetime | None) -> str:
    if not start or not end:
        return "daily"
    delta = end - start
    if delta <= timedelta(hours=25):
        return "hourly"
    if delta <= timedelta(days=8):
        return "daily"
    if delta <= timedelta(days=32):
        return "daily"
    if delta <= timedelta(days=95):
        return "weekly"
    return "monthly"


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _log_conditions(
        self,
        user_id: uuid.UUID | None,
        organization_id: uuid.UUID | None,
        start_date: datetime | None,
        end_date: datetime | None,
        provider: str | None = None,
        model: str | None = None,
        api_key_id: uuid.UUID | None = None,
    ) -> list:
        conditions = []
        if user_id:
            conditions.append(RequestLog.user_id == user_id)
        if organization_id:
            conditions.append(RequestLog.organization_id == organization_id)
        if start_date:
            conditions.append(RequestLog.created_at >= start_date)
        if end_date:
            conditions.append(RequestLog.created_at <= end_date)
        if provider:
            conditions.append(RequestLog.provider.ilike(f"%{provider}%"))
        if model:
            conditions.append(
                or_(
                    RequestLog.model.ilike(f"%{model}%"),
                    RequestLog.requested_model.ilike(f"%{model}%"),
                )
            )
        if api_key_id:
            conditions.append(RequestLog.api_key_id == api_key_id)
        return conditions

    async def overview(
        self,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        conditions = self._log_conditions(user_id, organization_id, start_date, end_date)
        where = and_(*conditions) if conditions else True

        total_q = select(func.count(RequestLog.id)).where(where)
        success_q = select(func.count(RequestLog.id)).where(where, _success_condition())
        failed_q = select(func.count(RequestLog.id)).where(where, _failed_condition())
        latency_q = select(func.avg(RequestLog.latency_ms)).where(where, _success_condition())

        total = (await self.db.execute(total_q)).scalar() or 0
        success = (await self.db.execute(success_q)).scalar() or 0
        failed = (await self.db.execute(failed_q)).scalar() or 0
        avg_latency = (await self.db.execute(latency_q)).scalar() or 0

        usage_svc = UsageService(self.db)
        cost_svc = CostService(self.db)
        usage = await usage_svc.get_total_usage(user_id, organization_id, start_date, end_date)
        total_cost = await cost_svc.get_total_cost(user_id, organization_id, start_date, end_date)

        # Active providers/models from request data
        active_providers_q = (
            select(func.count(func.distinct(RequestLog.provider)))
            .where(where)
            .where(RequestLog.provider != "pending")
        )
        active_models_q = select(func.count(func.distinct(RequestLog.model))).where(where)

        active_providers = (await self.db.execute(active_providers_q)).scalar() or 0
        active_models = (await self.db.execute(active_models_q)).scalar() or 0

        if total == 0:
            return {
                "has_data": False,
                "message": "No request data available yet.",
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "success_rate": 0.0,
                "total_tokens": 0,
                "estimated_total_cost": 0.0,
                "average_latency_ms": 0.0,
                "active_providers": 0,
                "active_models": 0,
            }

        return {
            "has_data": True,
            "total_requests": total,
            "successful_requests": success,
            "failed_requests": failed,
            "success_rate": round((success / total * 100) if total else 0, 2),
            "total_tokens": usage["total_tokens"],
            "total_input_tokens": usage["total_input_tokens"],
            "total_output_tokens": usage["total_output_tokens"],
            "estimated_total_cost": round(total_cost, 6),
            "cost_disclaimer": "Estimated cost — may not match provider invoices.",
            "average_latency_ms": round(avg_latency, 2),
            "active_providers": active_providers,
            "active_models": active_models,
        }

    async def time_series(
        self,
        metric: str,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        bucket = _choose_bucket(start_date, end_date)
        conditions = self._log_conditions(user_id, organization_id, start_date, end_date)
        where = and_(*conditions) if conditions else True

        if bucket == "hourly":
            trunc = func.date_trunc("hour", RequestLog.created_at)
        elif bucket == "weekly":
            trunc = func.date_trunc("week", RequestLog.created_at)
        elif bucket == "monthly":
            trunc = func.date_trunc("month", RequestLog.created_at)
        else:
            trunc = func.date_trunc("day", RequestLog.created_at)

        if metric == "requests":
            query = (
                select(trunc.label("period"), func.count(RequestLog.id).label("value"))
                .where(where)
                .group_by(trunc)
                .order_by(trunc)
            )
        elif metric == "latency":
            query = (
                select(trunc.label("period"), func.avg(RequestLog.latency_ms).label("value"))
                .where(where, _success_condition())
                .group_by(trunc)
                .order_by(trunc)
            )
        elif metric == "errors":
            query = (
                select(trunc.label("period"), func.count(RequestLog.id).label("value"))
                .where(where, _failed_condition())
                .group_by(trunc)
                .order_by(trunc)
            )
        else:
            # tokens or cost — use usage/cost tables
            if metric == "cost":
                table = CostRecord
                value_col = func.sum(CostRecord.total_cost)
                trunc_col = CostRecord.created_at
            else:
                table = UsageRecord
                value_col = func.sum(UsageRecord.total_tokens)
                trunc_col = UsageRecord.created_at

            if bucket == "hourly":
                trunc_u = func.date_trunc("hour", trunc_col)
            elif bucket == "weekly":
                trunc_u = func.date_trunc("week", trunc_col)
            elif bucket == "monthly":
                trunc_u = func.date_trunc("month", trunc_col)
            else:
                trunc_u = func.date_trunc("day", trunc_col)

            u_conditions = []
            if user_id:
                u_conditions.append(table.user_id == user_id)
            if organization_id:
                u_conditions.append(table.organization_id == organization_id)
            if start_date:
                u_conditions.append(table.created_at >= start_date)
            if end_date:
                u_conditions.append(table.created_at <= end_date)

            query = (
                select(trunc_u.label("period"), value_col.label("value"))
                .where(and_(*u_conditions) if u_conditions else True)
                .group_by(trunc_u)
                .order_by(trunc_u)
            )

        rows = (await self.db.execute(query)).all()
        return {
            "bucket": bucket,
            "metric": metric,
            "data": [
                {"timestamp": row.period.isoformat() if row.period else None, "value": float(row.value or 0)}
                for row in rows
            ],
        }

    async def providers(
        self,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        conditions = self._log_conditions(user_id, organization_id, start_date, end_date)
        where = and_(*conditions) if conditions else True

        query = (
            select(
                RequestLog.provider,
                func.count(RequestLog.id).label("total_requests"),
                func.sum(case((_success_condition(), 1), else_=0)).label("success_count"),
                func.sum(case((_failed_condition(), 1), else_=0)).label("failure_count"),
                func.avg(RequestLog.latency_ms).label("avg_latency"),
            )
            .where(where, RequestLog.provider != "pending")
            .group_by(RequestLog.provider)
            .order_by(func.count(RequestLog.id).desc())
        )
        rows = (await self.db.execute(query)).all()

        results = []
        for row in rows:
            total = row.total_requests or 0
            success = row.success_count or 0
            # Token and cost per provider
            token_q = select(func.sum(UsageRecord.total_tokens)).where(
                UsageRecord.provider == row.provider
            )
            cost_q = select(func.sum(CostRecord.total_cost)).where(
                CostRecord.provider == row.provider
            )
            if user_id:
                token_q = token_q.where(UsageRecord.user_id == user_id)
                cost_q = cost_q.where(CostRecord.user_id == user_id)
            if start_date:
                token_q = token_q.where(UsageRecord.created_at >= start_date)
                cost_q = cost_q.where(CostRecord.created_at >= start_date)
            if end_date:
                token_q = token_q.where(UsageRecord.created_at <= end_date)
                cost_q = cost_q.where(CostRecord.created_at <= end_date)

            tokens = (await self.db.execute(token_q)).scalar() or 0
            cost = (await self.db.execute(cost_q)).scalar() or 0

            results.append({
                "provider": row.provider,
                "total_requests": total,
                "success_rate": round((success / total * 100) if total else 0, 2),
                "average_latency_ms": round(row.avg_latency or 0, 2),
                "total_tokens": tokens,
                "estimated_cost": round(cost, 6),
                "error_count": row.failure_count or 0,
            })
        return results

    async def models(
        self,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        conditions = self._log_conditions(user_id, organization_id, start_date, end_date)
        where = and_(*conditions) if conditions else True

        query = (
            select(
                RequestLog.model,
                RequestLog.provider,
                func.count(RequestLog.id).label("total_requests"),
                func.sum(case((_success_condition(), 1), else_=0)).label("success_count"),
                func.avg(RequestLog.latency_ms).label("avg_latency"),
                func.sum(case((RequestLog.fallback_used.is_(True), 1), else_=0)).label("fallback_count"),
            )
            .where(where)
            .group_by(RequestLog.model, RequestLog.provider)
            .order_by(func.count(RequestLog.id).desc())
            .limit(50)
        )
        rows = (await self.db.execute(query)).all()

        results = []
        for row in rows:
            total = row.total_requests or 0
            token_q = select(func.sum(UsageRecord.total_tokens)).where(
                UsageRecord.model == row.model
            )
            cost_q = select(func.sum(CostRecord.total_cost)).where(
                CostRecord.model == row.model
            )
            if user_id:
                token_q = token_q.where(UsageRecord.user_id == user_id)
                cost_q = cost_q.where(CostRecord.user_id == user_id)

            tokens = (await self.db.execute(token_q)).scalar() or 0
            cost = (await self.db.execute(cost_q)).scalar() or 0

            results.append({
                "model": row.model,
                "provider": row.provider,
                "total_requests": total,
                "success_rate": round(((row.success_count or 0) / total * 100) if total else 0, 2),
                "average_latency_ms": round(row.avg_latency or 0, 2),
                "total_tokens": tokens,
                "estimated_cost": round(cost, 6),
                "fallback_rate": round(((row.fallback_count or 0) / total * 100) if total else 0, 2),
            })
        return results

    async def errors(
        self,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 50,
    ) -> list[dict]:
        conditions = self._log_conditions(user_id, organization_id, start_date, end_date)
        conditions.append(_failed_condition())

        query = (
            select(RequestLog)
            .where(and_(*conditions))
            .order_by(RequestLog.created_at.desc())
            .limit(limit)
        )
        rows = (await self.db.execute(query)).scalars().all()

        return [
            {
                "request_id": r.request_id,
                "error_type": r.error_type or "INTERNAL_ERROR",
                "error_code": r.error_code,
                "provider": r.provider,
                "model": r.model,
                "timestamp": r.created_at.isoformat(),
                "message": r.error,
            }
            for r in rows
        ]

    async def api_key_usage(
        self,
        user_id: uuid.UUID | None = None,
    ) -> list[dict]:
        from app.models.api_key import APIKey

        query = select(APIKey)
        if user_id:
            query = query.where(APIKey.user_id == user_id)
        keys = (await self.db.execute(query)).scalars().all()

        results = []
        for key in keys:
            req_q = select(func.count(RequestLog.id)).where(RequestLog.api_key_id == key.id)
            token_q = select(func.sum(UsageRecord.total_tokens)).where(
                UsageRecord.request_id.in_(
                    select(RequestLog.request_id).where(RequestLog.api_key_id == key.id)
                )
            )
            cost_q = select(func.sum(CostRecord.total_cost)).where(
                CostRecord.request_id.in_(
                    select(RequestLog.request_id).where(RequestLog.api_key_id == key.id)
                )
            )

            results.append({
                "id": str(key.id),
                "name": key.name,
                "prefix": key.key_prefix,
                "created_at": key.created_at.isoformat() if key.created_at else None,
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                "request_count": (await self.db.execute(req_q)).scalar() or 0,
                "total_tokens": (await self.db.execute(token_q)).scalar() or 0,
                "estimated_cost": round((await self.db.execute(cost_q)).scalar() or 0, 6),
            })
        return results

    async def provider_performance(
        self,
        user_id: uuid.UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        """Provider performance with percentiles when enough data exists."""
        conditions = self._log_conditions(user_id, None, start_date, end_date)
        where = and_(*conditions) if conditions else True

        query = (
            select(
                RequestLog.provider,
                func.count(RequestLog.id).label("request_count"),
                func.sum(case((_success_condition(), 1), else_=0)).label("success_count"),
                func.sum(case((_failed_condition(), 1), else_=0)).label("failure_count"),
                func.avg(RequestLog.latency_ms).label("avg_latency"),
            )
            .where(where, RequestLog.provider != "pending")
            .group_by(RequestLog.provider)
        )
        rows = (await self.db.execute(query)).all()

        results = []
        for row in rows:
            total = row.request_count or 0
            entry: dict[str, Any] = {
                "provider": row.provider,
                "request_count": total,
                "success_count": row.success_count or 0,
                "failure_count": row.failure_count or 0,
                "success_rate": round(((row.success_count or 0) / total * 100) if total else 0, 2),
                "error_rate": round(((row.failure_count or 0) / total * 100) if total else 0, 2),
                "average_latency_ms": round(row.avg_latency or 0, 2),
            }

            # Percentiles only with enough samples (>= 20)
            if total >= 20:
                lat_q = (
                    select(RequestLog.latency_ms)
                    .where(where, RequestLog.provider == row.provider, _success_condition())
                    .order_by(RequestLog.latency_ms)
                )
                latencies = [r for r in (await self.db.execute(lat_q)).scalars().all()]
                if latencies:
                    p50_idx = int(len(latencies) * 0.5)
                    p95_idx = int(len(latencies) * 0.95)
                    entry["p50_latency_ms"] = round(latencies[p50_idx], 2)
                    entry["p95_latency_ms"] = round(latencies[min(p95_idx, len(latencies) - 1)], 2)
            else:
                entry["p50_latency_ms"] = None
                entry["p95_latency_ms"] = None
                entry["percentile_note"] = "Insufficient data for percentiles (need >= 20 requests)"

            results.append(entry)
        return results
