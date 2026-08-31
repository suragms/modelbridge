"""Provider performance analysis and recommendations."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import AutomationLevel, RecommendationCategory
from app.services.intelligence.data_quality import MIN_SAMPLES_PROVIDER, assess_quality
from app.services.intelligence.foundation import OperationalDataFoundation
from app.services.intelligence.recommendations import RecommendationService


class ProviderIntelligenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.foundation = OperationalDataFoundation(db)
        self.recommendations = RecommendationService(db)

    async def analyze(self, organization_id: uuid.UUID, *, days: int = 7) -> dict[str, Any]:
        signals = await self.foundation.collect_signals(organization_id, *self.foundation.default_window(days))
        providers = signals["provider_performance"]
        overview = signals["overview"]

        quality = assess_quality(
            sample_size=overview.get("total_requests", 0),
            min_samples=MIN_SAMPLES_PROVIDER,
            missing=[] if overview.get("has_data") else ["no_request_logs"],
        )

        if quality.status == "insufficient_data":
            return {
                "status": "insufficient_data",
                "data_quality": quality.to_dict(),
                "providers": [],
                "recommendations": [],
                "message": "Not enough request data for provider analysis.",
            }

        ranked = sorted(
            providers,
            key=lambda p: (p.get("success_rate", 0), -p.get("average_latency_ms", 9999)),
            reverse=True,
        )

        analysis = []
        for p in ranked:
            entry = {
                "provider": p["provider"],
                "request_count": p["request_count"],
                "success_rate": p["success_rate"],
                "error_rate": p["error_rate"],
                "average_latency_ms": p["average_latency_ms"],
                "p50_latency_ms": p.get("p50_latency_ms"),
                "p95_latency_ms": p.get("p95_latency_ms"),
                "reliability_score": self._reliability_score(p),
            }
            entry["explanation"] = self._explain(p, ranked[0] if ranked else None)
            analysis.append(entry)

        recs = await self._generate_recommendations(organization_id, ranked, quality)
        return {
            "status": "ok",
            "data_quality": quality.to_dict(),
            "providers": analysis,
            "best_provider": ranked[0]["provider"] if ranked else None,
            "recommendations_created": len(recs),
        }

    def _reliability_score(self, p: dict) -> float:
        success = p.get("success_rate", 0) / 100
        latency = p.get("average_latency_ms", 0)
        latency_factor = max(0, 1 - min(latency / 10000, 1))
        return round(success * 0.7 + latency_factor * 0.3, 3)

    def _explain(self, provider: dict, best: dict | None) -> str:
        if not best:
            return "Insufficient comparison data."
        if provider["provider"] == best["provider"]:
            return (
                f"{provider['provider']} has the highest recent success rate "
                f"({provider['success_rate']}%) with average latency "
                f"{provider['average_latency_ms']}ms among observed providers."
            )
        return (
            f"{provider['provider']} shows {provider['success_rate']}% success rate "
            f"and {provider['average_latency_ms']}ms average latency in the observed window."
        )

    async def _generate_recommendations(
        self, organization_id: uuid.UUID, ranked: list[dict], quality
    ) -> list:
        created = []
        if len(ranked) < 2:
            return created

        best = ranked[0]
        worst = min(ranked, key=lambda p: p.get("success_rate", 0))
        if worst["error_rate"] > 10 and worst["request_count"] >= MIN_SAMPLES_PROVIDER:
            rec = await self.recommendations.create(
                organization_id=organization_id,
                category=RecommendationCategory.ROUTING,
                title=f"Consider reducing traffic to {worst['provider']}",
                description=(
                    f"{worst['provider']} has an error rate of {worst['error_rate']}% "
                    f"over {worst['request_count']} requests."
                ),
                evidence={
                    "provider": worst["provider"],
                    "error_rate": worst["error_rate"],
                    "request_count": worst["request_count"],
                    "supporting_metrics": ["error_rate", "request_count"],
                },
                suggested_action=f"Prefer {best['provider']} or investigate {worst['provider']} health.",
                confidence=quality.confidence * 0.9,
                risks="Routing changes require approval and may affect latency for some models.",
                automation_level=AutomationLevel.APPROVAL_REQUIRED,
            )
            created.append(rec)

        if best["success_rate"] > 95 and best["request_count"] >= MIN_SAMPLES_PROVIDER:
            rec = await self.recommendations.create(
                organization_id=organization_id,
                category=RecommendationCategory.PERFORMANCE,
                title=f"Prefer {best['provider']} for eligible traffic",
                description=(
                    f"{best['provider']} is recommended because its recent success rate "
                    f"({best['success_rate']}%) is highest while latency remains "
                    f"{best['average_latency_ms']}ms within the observed window."
                ),
                evidence={
                    "provider": best["provider"],
                    "success_rate": best["success_rate"],
                    "average_latency_ms": best["average_latency_ms"],
                    "supporting_metrics": ["success_rate", "latency"],
                },
                suggested_action="Review routing policy to prefer this provider where governance allows.",
                confidence=quality.confidence,
                automation_level=AutomationLevel.RECOMMEND,
            )
            created.append(rec)
        return created
