"""FinOps overview, explorer, and model comparison."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finops import ALLOWED_TAG_KEYS, FinopsCostAttribution, FinopsCostSnapshot
from app.models.request_log import CostRecord, UsageRecord
from app.services.finops.engine import CostEngine


def validate_tags(tags: dict) -> list[str]:
    errors = []
    for key in tags:
        if key not in ALLOWED_TAG_KEYS:
            errors.append(f"Invalid tag key: {key}")
    return errors


class OverviewService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine = CostEngine(db)

    async def overview(self, org_id: uuid.UUID) -> dict:
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        spend = await self.engine.org_spend(org_id, start=month_start, end=now)

        top_models = await self.db.execute(
            select(
                CostRecord.model,
                func.sum(CostRecord.total_cost),
                func.count(),
            )
            .where(CostRecord.organization_id == org_id, CostRecord.created_at >= month_start)
            .group_by(CostRecord.model)
            .order_by(func.sum(CostRecord.total_cost).desc())
            .limit(5)
        )

        return {
            "current_spend": spend["total_cost"],
            "cost_type": spend["cost_type"],
            "request_count": spend["request_count"],
            "period": "current_month",
            "top_cost_drivers": [
                {"model": r[0], "cost": float(r[1] or 0), "requests": int(r[2] or 0)}
                for r in top_models.all()
            ],
        }

    async def explore(
        self,
        org_id: uuid.UUID,
        *,
        days: int = 30,
        provider: str | None = None,
        model: str | None = None,
        project_id: uuid.UUID | None = None,
        team: str | None = None,
        breakdown: str = "provider",
    ) -> dict:
        start = datetime.now(UTC) - timedelta(days=days)
        end = datetime.now(UTC)

        base = select(CostRecord).where(
            CostRecord.organization_id == org_id,
            CostRecord.created_at >= start,
            CostRecord.created_at <= end,
        )
        if provider:
            base = base.where(CostRecord.provider == provider)
        if model:
            base = base.where(CostRecord.model == model)

        spend = await self.engine.org_spend(org_id, start=start, end=end, provider=provider, model=model)

        dim_col = {
            "provider": CostRecord.provider,
            "model": CostRecord.model,
        }.get(breakdown, CostRecord.provider)

        breakdown_q = await self.db.execute(
            select(
                dim_col,
                func.sum(CostRecord.total_cost),
                func.count(),
            )
            .where(
                CostRecord.organization_id == org_id,
                CostRecord.created_at >= start,
            )
            .group_by(dim_col)
            .order_by(func.sum(CostRecord.total_cost).desc())
            .limit(20)
        )

        return {
            "total_cost": spend["total_cost"],
            "cost_type": spend["cost_type"],
            "period_days": days,
            "breakdown": [
                {"key": r[0], "cost": float(r[1] or 0), "requests": int(r[2] or 0)}
                for r in breakdown_q.all()
            ],
        }

    async def model_comparison(self, org_id: uuid.UUID, *, days: int = 30) -> list[dict]:
        start = datetime.now(UTC) - timedelta(days=days)
        result = await self.db.execute(
            select(
                CostRecord.model,
                CostRecord.provider,
                func.sum(CostRecord.total_cost),
                func.sum(CostRecord.input_cost),
                func.sum(CostRecord.output_cost),
                func.count(),
                func.avg(CostRecord.total_cost),
            )
            .where(CostRecord.organization_id == org_id, CostRecord.created_at >= start)
            .group_by(CostRecord.model, CostRecord.provider)
            .order_by(func.sum(CostRecord.total_cost).desc())
            .limit(20)
        )

        latency_q = await self.db.execute(
            select(
                CostRecord.model,
                func.avg(UsageRecord.total_tokens),
            )
            .join(UsageRecord, UsageRecord.request_id == CostRecord.request_id)
            .where(CostRecord.organization_id == org_id, CostRecord.created_at >= start)
            .group_by(CostRecord.model)
        )
        tokens_by_model = {r[0]: float(r[1] or 0) for r in latency_q.all()}

        return [
            {
                "model": r[0],
                "provider": r[1],
                "total_cost": float(r[2] or 0),
                "input_cost": float(r[3] or 0),
                "output_cost": float(r[4] or 0),
                "request_count": int(r[5] or 0),
                "avg_request_cost": float(r[6] or 0),
                "avg_tokens": tokens_by_model.get(r[0]),
                "cost_type": "estimated",
                "methodology": "Aggregated from CostRecord entries using configured pricing",
            }
            for r in result.all()
        ]

    async def attribute_cost(
        self,
        *,
        org_id: uuid.UUID,
        request_id: str,
        user_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        workspace_id: uuid.UUID | None = None,
        environment_id: uuid.UUID | None = None,
        team: str | None = None,
        application: str | None = None,
        tags: dict | None = None,
    ) -> FinopsCostAttribution:
        tag_errors = validate_tags(tags or {})
        if tag_errors:
            raise ValueError("; ".join(tag_errors))

        attr = FinopsCostAttribution(
            organization_id=org_id,
            request_id=request_id,
            user_id=user_id,
            project_id=project_id,
            workspace_id=workspace_id,
            environment_id=environment_id,
            team=team,
            application=application,
            tags=tags or {},
        )
        self.db.add(attr)
        await self.db.flush()
        return attr

    async def aggregate_snapshots(self, org_id: uuid.UUID, *, days: int = 1) -> int:
        start = datetime.now(UTC) - timedelta(days=days)
        end = datetime.now(UTC)
        period_date = start.replace(hour=0, minute=0, second=0, microsecond=0)

        by_provider = await self.db.execute(
            select(
                CostRecord.provider,
                func.sum(CostRecord.total_cost),
                func.count(),
            )
            .where(CostRecord.organization_id == org_id, CostRecord.created_at >= start, CostRecord.created_at <= end)
            .group_by(CostRecord.provider)
        )
        count = 0
        for row in by_provider.all():
            self.db.add(
                FinopsCostSnapshot(
                    organization_id=org_id,
                    period_date=period_date,
                    dimension="provider",
                    dimension_key=row[0],
                    total_cost=float(row[1] or 0),
                    request_count=int(row[2] or 0),
                    cost_type="estimated",
                )
            )
            count += 1
        await self.db.flush()
        return count
