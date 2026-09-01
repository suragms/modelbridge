"""Regression comparison and detection."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quality import (
    QualityEvaluationRun,
    QualityRegressionComparison,
    RegressionStatus,
)
from app.services.metrics import record_quality_regression
from app.services.platform.events import EventBus


class RegressionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def compare_runs(
        self,
        *,
        org_id: uuid.UUID,
        comparison_type: str,
        baseline_label: str,
        candidate_label: str,
        baseline_run_id: uuid.UUID,
        candidate_run_id: uuid.UUID,
        thresholds: dict | None,
        user_id: uuid.UUID | None,
    ) -> QualityRegressionComparison:
        baseline = await self._get_run(org_id, baseline_run_id)
        candidate = await self._get_run(org_id, candidate_run_id)
        if not baseline or not candidate:
            raise ValueError("Run not found")

        thresholds = thresholds or {
            "max_pass_rate_drop": 0.05,
            "max_latency_increase_pct": 0.25,
            "max_cost_increase_pct": 0.25,
        }

        baseline_rate = baseline.pass_rate or 0.0
        candidate_rate = candidate.pass_rate or 0.0
        rate_drop = baseline_rate - candidate_rate

        baseline_latency = baseline.total_latency_ms or 0
        candidate_latency = candidate.total_latency_ms or 0
        latency_delta_pct = (
            (candidate_latency - baseline_latency) / baseline_latency if baseline_latency > 0 else 0
        )

        baseline_cost = baseline.total_cost or 0
        candidate_cost = candidate.total_cost or 0
        cost_delta_pct = (
            (candidate_cost - baseline_cost) / baseline_cost if baseline_cost > 0 else 0
        )

        metrics = {
            "baseline_pass_rate": baseline_rate,
            "candidate_pass_rate": candidate_rate,
            "baseline_latency_ms": baseline_latency,
            "candidate_latency_ms": candidate_latency,
            "baseline_cost": baseline_cost,
            "candidate_cost": candidate_cost,
            "baseline_fail_count": baseline.fail_count,
            "candidate_fail_count": candidate.fail_count,
        }
        differences = {
            "pass_rate_drop": rate_drop,
            "latency_increase_pct": latency_delta_pct,
            "cost_increase_pct": cost_delta_pct,
        }

        regressions: list[str] = []
        if rate_drop > thresholds.get("max_pass_rate_drop", 0.05):
            regressions.append("quality_drop")
        if latency_delta_pct > thresholds.get("max_latency_increase_pct", 0.25):
            regressions.append("latency_regression")
        if cost_delta_pct > thresholds.get("max_cost_increase_pct", 0.25):
            regressions.append("cost_regression")
        if candidate.fail_count > baseline.fail_count:
            regressions.append("failure_increase")

        status = RegressionStatus.REGRESSION_DETECTED if regressions else RegressionStatus.NO_REGRESSION

        comparison = QualityRegressionComparison(
            organization_id=org_id,
            comparison_type=comparison_type,
            baseline_label=baseline_label,
            candidate_label=candidate_label,
            baseline_run_id=baseline_run_id,
            candidate_run_id=candidate_run_id,
            metrics=metrics,
            differences={**differences, "regressions": regressions},
            status=status,
            thresholds=thresholds,
            created_by=user_id,
        )
        self.db.add(comparison)
        await self.db.flush()

        record_quality_regression(status=status)
        if regressions:
            await EventBus(self.db).emit(
                organization_id=org_id,
                event_type="quality.regression.detected",
                data={"status": status, "execution_id": str(comparison.id)},
                source="quality",
            )
            from app.services.quality.alerts import AlertService

            await AlertService(self.db).create_regression_alert(org_id=org_id, comparison=comparison)

        await self.db.flush()
        return comparison

    async def compare_prompt_versions(
        self,
        *,
        org_id: uuid.UUID,
        pipeline_id: uuid.UUID,
        baseline_prompt_version_id: uuid.UUID,
        candidate_prompt_version_id: uuid.UUID,
        user_id: uuid.UUID | None,
        pipeline_service,
    ) -> QualityRegressionComparison:
        from app.models.quality import QualityPipeline, QualityPipelineVersion

        pipeline = await self.db.get(QualityPipeline, pipeline_id)
        if not pipeline or pipeline.organization_id != org_id:
            raise ValueError("Pipeline not found")

        version = await self.db.get(QualityPipelineVersion, pipeline.current_version_id)
        if not version:
            raise ValueError("No pipeline version")

        original_prompt = version.prompt_version_id
        version.prompt_version_id = baseline_prompt_version_id
        await self.db.flush()
        baseline_run = await pipeline_service.run(pipeline, org_id=org_id, user_id=user_id, trigger="regression")

        version.prompt_version_id = candidate_prompt_version_id
        await self.db.flush()
        candidate_run = await pipeline_service.run(pipeline, org_id=org_id, user_id=user_id, trigger="regression")

        version.prompt_version_id = original_prompt
        await self.db.flush()

        return await self.compare_runs(
            org_id=org_id,
            comparison_type="prompt",
            baseline_label=f"prompt_v{baseline_prompt_version_id}",
            candidate_label=f"prompt_v{candidate_prompt_version_id}",
            baseline_run_id=baseline_run.id,
            candidate_run_id=candidate_run.id,
            thresholds=None,
            user_id=user_id,
        )

    async def list_comparisons(self, org_id: uuid.UUID, limit: int = 50) -> list[QualityRegressionComparison]:
        result = await self.db.execute(
            select(QualityRegressionComparison)
            .where(QualityRegressionComparison.organization_id == org_id)
            .order_by(QualityRegressionComparison.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _get_run(self, org_id: uuid.UUID, run_id: uuid.UUID) -> QualityEvaluationRun | None:
        run = await self.db.get(QualityEvaluationRun, run_id)
        if not run or run.organization_id != org_id:
            return None
        return run
