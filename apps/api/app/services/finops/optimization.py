"""Explainable optimization recommendations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finops import (
    FinopsOptimizationRecommendation,
    RecommendationStatus,
    SavingsStatus,
)
from app.models.request_log import CostRecord
from app.services.metrics import record_finops_optimization
from app.services.platform.events import EventBus


class OptimizationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze(self, org_id: uuid.UUID, *, days: int = 30) -> list[FinopsOptimizationRecommendation]:
        end = datetime.now(UTC)
        start = end - timedelta(days=days)
        recommendations: list[FinopsOptimizationRecommendation] = []

        by_model = await self.db.execute(
            select(
                CostRecord.model,
                CostRecord.provider,
                func.sum(CostRecord.total_cost),
                func.count(),
                func.avg(CostRecord.total_cost),
            )
            .where(
                CostRecord.organization_id == org_id,
                CostRecord.created_at >= start,
            )
            .group_by(CostRecord.model, CostRecord.provider)
            .order_by(func.sum(CostRecord.total_cost).desc())
            .limit(10)
        )
        models = by_model.all()
        total = sum(float(r[2] or 0) for r in models)

        if models and total > 0:
            top = models[0]
            top_cost = float(top[2] or 0)
            if top_cost > total * 0.5 and len(models) >= 2:
                rec = FinopsOptimizationRecommendation(
                    organization_id=org_id,
                    category="model_right_sizing",
                    title=f"Review high-cost model: {top[0]}",
                    description=(
                        f"Model {top[0]} ({top[1]}) accounts for {top_cost/total*100:.0f}% of spend. "
                        "Consider evaluating lower-cost alternatives for suitable workloads."
                    ),
                    evidence={
                        "model": top[0],
                        "provider": top[1],
                        "cost": top_cost,
                        "total_cost": total,
                        "share_percent": round(top_cost / total * 100, 1),
                        "request_count": int(top[3] or 0),
                    },
                    projected_savings=round(top_cost * 0.2, 4),
                    savings_status=SavingsStatus.PROJECTED,
                    assumptions="20% savings if 20% of requests can use a cheaper model with acceptable quality",
                    confidence="medium",
                    risk="medium — quality impact must be validated via Phase 17 evaluations",
                )
                recommendations.append(rec)
                self.db.add(rec)

        cache_rec = FinopsOptimizationRecommendation(
            organization_id=org_id,
            category="caching_opportunity",
            title="Evaluate response caching for repeated prompts",
            description=(
                "Phase 7 response caching can reduce duplicate inference costs. "
                "Review request patterns for cacheable workloads."
            ),
            evidence={"source": "platform_capability", "phase": "7"},
            projected_savings=None,
            savings_status=SavingsStatus.UNVERIFIED,
            assumptions="Savings depend on cache hit rate; measure after enabling caching",
            confidence="low",
            risk="low",
        )
        recommendations.append(cache_rec)
        self.db.add(cache_rec)

        for rec in recommendations:
            await self.db.flush()
            record_finops_optimization(status="created")
            await EventBus(self.db).emit(
                organization_id=org_id,
                event_type="optimization.recommendation.created",
                data={"status": rec.category, "execution_id": str(rec.id)},
                source="finops",
            )

        await self.db.flush()
        return recommendations

    async def list_recommendations(self, org_id: uuid.UUID) -> list[FinopsOptimizationRecommendation]:
        result = await self.db.execute(
            select(FinopsOptimizationRecommendation)
            .where(FinopsOptimizationRecommendation.organization_id == org_id)
            .order_by(FinopsOptimizationRecommendation.created_at.desc())
            .limit(50)
        )
        return list(result.scalars().all())

    async def approve(
        self,
        org_id: uuid.UUID,
        rec_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> FinopsOptimizationRecommendation | None:
        rec = await self.db.get(FinopsOptimizationRecommendation, rec_id)
        if not rec or rec.organization_id != org_id:
            return None
        rec.status = RecommendationStatus.APPROVED
        rec.approved_by = user_id
        await self.db.flush()
        return rec
