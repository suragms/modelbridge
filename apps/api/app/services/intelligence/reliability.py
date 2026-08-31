"""Explainable reliability scoring."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.intelligence.foundation import OperationalDataFoundation


class ReliabilityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.foundation = OperationalDataFoundation(db)

    async def score(self, organization_id: uuid.UUID, *, days: int = 7) -> dict[str, Any]:
        signals = await self.foundation.collect_signals(organization_id, *self.foundation.default_window(days))
        overview = signals["overview"]

        if not overview.get("has_data"):
            return {
                "status": "insufficient_data",
                "message": "No request data for reliability scoring.",
            }

        availability = overview.get("success_rate", 0) / 100
        error_rate = 1 - availability
        latency = overview.get("average_latency_ms", 0)
        latency_stability = max(0, 1 - min(latency / 5000, 1))

        agent_fail = signals["agents"].get("failure_rate", 0) / 100
        recovery = 1 - min(agent_fail, 1)

        overall = round(
            availability * 0.4 + latency_stability * 0.3 + recovery * 0.3,
            3,
        )

        health = "healthy"
        if overall < 0.7:
            health = "critical"
        elif overall < 0.85:
            health = "at_risk"
        elif overall < 0.95:
            health = "watch"

        return {
            "status": "ok",
            "overall_score": overall,
            "operational_health": health,
            "dimensions": {
                "availability": {
                    "score": round(availability, 3),
                    "success_rate_pct": overview.get("success_rate"),
                    "explanation": "Based on completed vs failed requests in the window.",
                },
                "error_rate": {
                    "score": round(1 - error_rate, 3),
                    "failed_requests": overview.get("failed_requests"),
                },
                "latency_stability": {
                    "score": round(latency_stability, 3),
                    "average_latency_ms": latency,
                    "explanation": "Higher scores when average latency is lower.",
                },
                "recovery_performance": {
                    "score": round(recovery, 3),
                    "agent_failure_rate_pct": signals["agents"].get("failure_rate"),
                },
            },
            "calculation": "Weighted: availability 40%, latency stability 30%, agent recovery 30%.",
        }
