"""Safe natural-language operations assistant (rule-based, no raw SQL)."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.intelligence.anomalies import AnomalyService
from app.services.intelligence.cost import CostIntelligenceService
from app.services.intelligence.foundation import OperationalDataFoundation
from app.services.intelligence.providers import ProviderIntelligenceService
from app.services.intelligence.reliability import ReliabilityService


class OperationsAssistant:
    """Maps authorized queries to safe intelligence service calls."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.foundation = OperationalDataFoundation(db)
        self.providers = ProviderIntelligenceService(db)
        self.costs = CostIntelligenceService(db)
        self.reliability = ReliabilityService(db)
        self.anomalies = AnomalyService(db)

    async def query(self, organization_id: uuid.UUID, question: str) -> dict[str, Any]:
        q = question.lower().strip()
        if not q:
            return {"status": "error", "message": "Question cannot be empty."}

        intent = self._classify(q)
        evidence_sources: list[str] = []
        answer_parts: list[str] = []
        confidence = 0.5
        data: dict = {}

        if intent == "latency":
            signals = await self.foundation.collect_signals(organization_id)
            evidence_sources.append("latency_metrics")
            overview = signals["overview"]
            if not overview.get("has_data"):
                return self._insufficient("latency metrics")
            answer_parts.append(
                f"Average latency is {overview['average_latency_ms']}ms over "
                f"{overview['total_requests']} requests in the last 7 days."
            )
            confidence = 0.85
            data["overview"] = overview

        elif intent == "best_provider":
            analysis = await self.providers.analyze(organization_id)
            evidence_sources.append("provider_health")
            evidence_sources.append("latency_metrics")
            if analysis.get("status") == "insufficient_data":
                return self._insufficient("provider performance data")
            best = analysis.get("best_provider")
            answer_parts.append(
                f"Based on recent success rate and latency, the best-performing provider is {best}."
                if best
                else "No provider comparison available."
            )
            confidence = analysis["data_quality"].get("confidence", 0.5)
            data["providers"] = analysis.get("providers", [])[:5]

        elif intent == "spending":
            analysis = await self.costs.analyze(organization_id)
            evidence_sources.append("usage_data")
            if analysis.get("status") == "insufficient_data":
                return self._insufficient("cost records")
            answer_parts.append(
                f"Observed spend: ${analysis['total_cost']:.4f} "
                f"(actual: ${analysis['actual_cost']:.4f}, estimated: ${analysis['estimated_cost']:.4f})."
            )
            if analysis.get("by_model"):
                top = analysis["by_model"][0]
                answer_parts.append(f"Highest model spend: {top['model']} (${top['cost']:.4f}, {top['cost_type']} cost).")
            confidence = analysis["data_quality"].get("confidence", 0.5)
            data["costs"] = analysis

        elif intent == "errors":
            signals = await self.foundation.collect_signals(organization_id)
            evidence_sources.append("latency_metrics")
            overview = signals["overview"]
            if not overview.get("has_data"):
                return self._insufficient("error data")
            answer_parts.append(
                f"Failed requests: {overview['failed_requests']} "
                f"({100 - overview['success_rate']:.1f}% error rate)."
            )
            perf = signals.get("provider_performance", [])
            if perf:
                worst = min(perf, key=lambda p: p.get("success_rate", 100))
                answer_parts.append(
                    f"Highest error rate provider: {worst['provider']} ({worst['error_rate']}%)."
                )
            confidence = 0.8

        elif intent == "capacity":
            from app.services.intelligence.capacity import CapacityService

            analysis = await CapacityService(self.db).analyze(organization_id)
            evidence_sources.append("usage_data")
            if analysis.get("status") == "insufficient_data":
                return self._insufficient("capacity signals")
            answer_parts.append(
                f"Capacity health: {analysis['capacity_health']}. "
                f"Current daily requests: {analysis['current_daily_requests']}, "
                f"average: {analysis['average_daily_requests']}."
            )
            if analysis.get("risks"):
                answer_parts.append(analysis["risks"][0]["message"])
            confidence = analysis.get("forecast", {}).get("confidence", 0.5)
            data["capacity"] = analysis

        elif intent == "health":
            score = await self.reliability.score(organization_id)
            evidence_sources.append("provider_health")
            evidence_sources.append("latency_metrics")
            if score.get("status") == "insufficient_data":
                return self._insufficient("reliability data")
            answer_parts.append(
                f"Operational health: {score['operational_health']} "
                f"(reliability score: {score['overall_score']})."
            )
            confidence = 0.85
            data["reliability"] = score

        else:
            return {
                "status": "unsupported",
                "message": (
                    "I can help with: latency, provider performance, spending, errors, "
                    "capacity risks, and operational health. Try rephrasing your question."
                ),
                "supported_topics": ["latency", "best provider", "spending", "errors", "capacity", "health"],
            }

        return {
            "status": "ok",
            "question": question,
            "answer": " ".join(answer_parts),
            "interpretation": "Generated from operational metadata — not raw request content.",
            "evidence_sources": evidence_sources,
            "confidence": round(confidence, 3),
            "time_range": "last 7 days (default)",
            "data": data,
        }

    def _classify(self, q: str) -> str:
        if re.search(r"latenc|slow|response time", q):
            return "latency"
        if re.search(r"best|perform|provider|which provider", q):
            return "best_provider"
        if re.search(r"spend|cost|billing|money", q):
            return "spending"
        if re.search(r"error|fail|failure", q):
            return "errors"
        if re.search(r"capacity|scale|worker|load|risk", q):
            return "capacity"
        if re.search(r"health|status|reliab", q):
            return "health"
        if re.search(r"what changed|today", q):
            return "errors"
        return "unknown"

    def _insufficient(self, source: str) -> dict:
        return {
            "status": "insufficient_data",
            "message": f"Not enough {source} to answer this question.",
            "evidence_sources": [source],
            "confidence": 0,
        }
