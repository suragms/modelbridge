"""Cost intelligence and FinOps analysis."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import AutomationLevel, RecommendationCategory
from app.models.request_log import CostRecord, UsageRecord
from app.services.intelligence.data_quality import assess_quality
from app.services.intelligence.foundation import OperationalDataFoundation
from app.services.intelligence.recommendations import RecommendationService


class CostIntelligenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.foundation = OperationalDataFoundation(db)
        self.recommendations = RecommendationService(db)

    async def analyze(self, organization_id: uuid.UUID, *, days: int = 30) -> dict[str, Any]:
        start, end = self.foundation.default_window(days)
        signals = await self.foundation.collect_signals(organization_id, start=start, end=end)
        costs = signals["costs"]
        overview = signals["overview"]

        cost_records = await self.db.execute(
            select(func.count()).where(
                CostRecord.organization_id == organization_id,
                CostRecord.created_at >= start,
                CostRecord.created_at <= end,
            )
        )
        sample = cost_records.scalar() or 0
        quality = assess_quality(sample_size=sample, min_samples=5, time_start=start, time_end=end)

        if quality.status == "insufficient_data" and costs["total"] == 0:
            return {
                "status": "insufficient_data",
                "data_quality": quality.to_dict(),
                "message": "No cost data available for analysis.",
            }

        by_model = await self.db.execute(
            select(
                CostRecord.model,
                CostRecord.provider,
                func.sum(CostRecord.total_cost),
                func.sum(case((CostRecord.is_estimated.is_(True), 1), else_=0)),
                func.count(),
            )
            .where(
                CostRecord.organization_id == organization_id,
                CostRecord.created_at >= start,
                CostRecord.created_at <= end,
            )
            .group_by(CostRecord.model, CostRecord.provider)
            .order_by(func.sum(CostRecord.total_cost).desc())
            .limit(20)
        )

        model_breakdown = [
            {
                "model": r[0],
                "provider": r[1],
                "cost": round(float(r[2] or 0), 6),
                "estimated_records": int(r[3] or 0),
                "request_count": int(r[4] or 0),
                "cost_type": "estimated" if int(r[3] or 0) > 0 else "actual",
            }
            for r in by_model.all()
        ]

        optimizations = []
        if model_breakdown and len(model_breakdown) >= 2:
            top = model_breakdown[0]
            if top["cost"] > costs["total"] * 0.5:
                optimizations.append({
                    "type": "high_concentration",
                    "message": f"{top['model']} accounts for a majority of observed spend.",
                    "evidence": top,
                })

        recs = []
        if top_cost := (model_breakdown[0] if model_breakdown else None):
            if top_cost["cost"] > 0 and quality.status != "insufficient_data":
                rec = await self.recommendations.create(
                    organization_id=organization_id,
                    category=RecommendationCategory.COST,
                    title=f"Review usage of {top_cost['model']}",
                    description=(
                        f"{top_cost['model']} on {top_cost['provider']} represents "
                        f"${top_cost['cost']:.4f} of observed spend ({top_cost['cost_type']} cost)."
                    ),
                    evidence={
                        "model": top_cost["model"],
                        "provider": top_cost["provider"],
                        "cost": top_cost["cost"],
                        "cost_type": top_cost["cost_type"],
                        "supporting_metrics": ["cost_records"],
                    },
                    suggested_action="Evaluate lower-cost models for eligible workloads if quality requirements allow.",
                    confidence=quality.confidence,
                    risks="Cost reduction must not violate governance or quality policies.",
                    automation_level=AutomationLevel.RECOMMEND,
                )
                recs.append(rec)

        return {
            "status": "ok",
            "data_quality": quality.to_dict(),
            "total_cost": costs["total"],
            "actual_cost": costs["actual_cost"],
            "estimated_cost": costs["estimated_cost"],
            "cost_disclaimer": "Estimated costs may not match provider invoices.",
            "by_provider": costs["by_provider"],
            "by_model": model_breakdown,
            "optimization_opportunities": optimizations,
            "recommendations_created": len(recs),
        }
