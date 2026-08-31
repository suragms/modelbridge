"""Intelligence engine orchestrator."""

from __future__ import annotations

import uuid
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import IntelligenceJob, IntelligenceJobStatus
from app.services.intelligence.anomalies import AnomalyService
from app.services.intelligence.capacity import CapacityService
from app.services.intelligence.cost import CostIntelligenceService
from app.services.intelligence.foundation import OperationalDataFoundation
from app.services.intelligence.providers import ProviderIntelligenceService
from app.services.intelligence.recommendations import RecommendationService
from app.services.intelligence.reliability import ReliabilityService
from app.services.metrics import record_intelligence_job


class IntelligenceEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.foundation = OperationalDataFoundation(db)
        self.providers = ProviderIntelligenceService(db)
        self.costs = CostIntelligenceService(db)
        self.capacity = CapacityService(db)
        self.anomalies = AnomalyService(db)
        self.reliability = ReliabilityService(db)
        self.recommendations = RecommendationService(db)

    async def overview(self, organization_id: uuid.UUID) -> dict[str, Any]:
        signals = await self.foundation.collect_signals(organization_id)
        reliability = await self.reliability.score(organization_id)
        open_recs = await self.recommendations.list_recommendations(
            organization_id, status="open", limit=10
        )
        open_anomalies = await self.anomalies.list_anomalies(organization_id, status="open", limit=10)

        health = reliability.get("operational_health", "unknown")
        if signals["overview"].get("has_data") is False:
            health = "unknown"

        return {
            "operational_health": health,
            "reliability": reliability,
            "overview": signals["overview"],
            "data_quality": signals["data_quality"],
            "active_recommendations": len(open_recs),
            "open_anomalies": len(open_anomalies),
            "recommendations": [self._rec_summary(r) for r in open_recs[:5]],
            "anomalies": open_anomalies[:5],
            "automation_level": "recommend",
        }

    async def run_analysis(self, organization_id: uuid.UUID, job_type: str = "full") -> dict:
        job = IntelligenceJob(
            organization_id=organization_id,
            job_type=job_type,
            status=IntelligenceJobStatus.RUNNING,
        )
        from datetime import UTC, datetime

        job.started_at = datetime.now(UTC)
        self.db.add(job)
        await self.db.flush()
        start = time.time()
        summary: dict = {}

        try:
            if job_type in ("full", "providers"):
                summary["providers"] = await self.providers.analyze(organization_id)
            if job_type in ("full", "costs"):
                summary["costs"] = await self.costs.analyze(organization_id)
            if job_type in ("full", "capacity"):
                summary["capacity"] = await self.capacity.analyze(organization_id)
            if job_type in ("full", "anomalies"):
                summary["anomalies"] = await self.anomalies.detect(organization_id)

            job.status = IntelligenceJobStatus.SUCCESS
            job.result_summary = {
                k: {"status": v.get("status"), "recommendations_created": v.get("recommendations_created", v.get("anomalies_detected"))}
                for k, v in summary.items()
            }
            record_intelligence_job(status="success")
        except Exception as e:
            job.status = IntelligenceJobStatus.FAILED
            job.error_message = str(e)[:500]
            record_intelligence_job(status="failed")
            raise
        finally:
            from datetime import UTC, datetime

            job.completed_at = datetime.now(UTC)
            job.duration_ms = (time.time() - start) * 1000
            await self.db.flush()

        return {"job_id": str(job.id), "status": job.status, "summary": summary}

    async def job_health(self, organization_id: uuid.UUID) -> list[dict]:
        from sqlalchemy import select

        result = await self.db.execute(
            select(IntelligenceJob)
            .where(IntelligenceJob.organization_id == organization_id)
            .order_by(IntelligenceJob.created_at.desc())
            .limit(10)
        )
        return [
            {
                "job_type": j.job_type,
                "status": j.status,
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "duration_ms": j.duration_ms,
                "error": j.error_message,
            }
            for j in result.scalars().all()
        ]

    def _rec_summary(self, rec) -> dict:
        return {
            "id": str(rec.id),
            "category": rec.category,
            "title": rec.title,
            "severity": rec.severity,
            "confidence": rec.confidence,
            "status": rec.status,
        }
