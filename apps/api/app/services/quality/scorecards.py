"""Explainable quality and reliability scorecards."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quality import QualityEvaluationRun, QualityRunStatus, QualityScorecard
from app.models.request_log import RequestLog, SUCCESS_STATUSES


class ScorecardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_reliability(self, org_id: uuid.UUID, time_range: str = "7d") -> QualityScorecard:
        days = {"1d": 1, "7d": 7, "30d": 30}.get(time_range, 7)
        cutoff = datetime.now(UTC) - timedelta(days=days)

        total_result = await self.db.execute(
            select(func.count()).select_from(RequestLog).where(
                RequestLog.organization_id == org_id,
                RequestLog.created_at >= cutoff,
            )
        )
        total = total_result.scalar() or 0

        success_result = await self.db.execute(
            select(func.count())
            .select_from(RequestLog)
            .where(
                RequestLog.organization_id == org_id,
                RequestLog.created_at >= cutoff,
                RequestLog.status.in_(SUCCESS_STATUSES),
            )
        )
        success = success_result.scalar() or 0

        avg_latency_result = await self.db.execute(
            select(func.avg(RequestLog.latency_ms)).where(
                RequestLog.organization_id == org_id,
                RequestLog.created_at >= cutoff,
            )
        )
        avg_latency = float(avg_latency_result.scalar() or 0)

        error_rate = 1.0 - (success / total) if total > 0 else None
        availability = success / total if total > 0 else None

        runs_result = await self.db.execute(
            select(QualityEvaluationRun)
            .where(
                QualityEvaluationRun.organization_id == org_id,
                QualityEvaluationRun.status == QualityRunStatus.COMPLETED,
                QualityEvaluationRun.completed_at >= cutoff,
            )
        )
        runs = list(runs_result.scalars().all())
        quality_scores = [r.pass_rate for r in runs if r.pass_rate is not None]
        output_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None

        dimensions = {
            "availability": {
                "value": availability,
                "formula": "successful_requests / total_requests",
                "sample_count": total,
            },
            "latency": {
                "value": avg_latency,
                "formula": "average(request.latency_ms)",
                "unit": "ms",
                "sample_count": total,
            },
            "error_rate": {
                "value": error_rate,
                "formula": "failed_requests / total_requests",
                "sample_count": total,
            },
            "output_quality": {
                "value": output_quality,
                "formula": "average(evaluation_run.pass_rate)",
                "sample_count": len(quality_scores),
                "limitations": "Requires completed quality evaluation runs in time range",
            },
            "safety_compliance": {
                "value": None,
                "formula": "average(safety_evaluator.pass_rate)",
                "limitations": "Computed when safety evaluators are configured in pipelines",
            },
        }

        scores = [v for v in (availability, 1.0 - (error_rate or 1.0) if error_rate is not None else None, output_quality) if v is not None]
        overall = sum(scores) / len(scores) if scores else None

        confidence = "high" if total >= 100 else ("medium" if total >= 10 else "low")

        scorecard = QualityScorecard(
            organization_id=org_id,
            scorecard_type="reliability",
            time_range=time_range,
            overall_score=overall,
            dimensions=dimensions,
            formula="weighted average of availability, (1 - error_rate), and output_quality where data exists",
            inputs={"request_log_count": total, "evaluation_run_count": len(runs)},
            limitations=(
                "Reliability scorecards combine gateway telemetry and evaluation runs. "
                "Output quality requires explicit evaluation pipeline runs. "
                "Low sample counts reduce confidence."
            ),
            confidence=confidence if total > 0 else "insufficient_data",
        )
        self.db.add(scorecard)
        await self.db.flush()
        return scorecard

    async def compute_quality(self, org_id: uuid.UUID, time_range: str = "7d") -> QualityScorecard:
        days = {"1d": 1, "7d": 7, "30d": 30}.get(time_range, 7)
        cutoff = datetime.now(UTC) - timedelta(days=days)

        runs_result = await self.db.execute(
            select(QualityEvaluationRun)
            .where(
                QualityEvaluationRun.organization_id == org_id,
                QualityEvaluationRun.status == QualityRunStatus.COMPLETED,
                QualityEvaluationRun.completed_at >= cutoff,
            )
        )
        runs = list(runs_result.scalars().all())

        if not runs:
            scorecard = QualityScorecard(
                organization_id=org_id,
                scorecard_type="quality",
                time_range=time_range,
                overall_score=None,
                dimensions={},
                formula="average(pass_rate) across quality evaluation runs",
                inputs={"run_count": 0},
                limitations="No evaluation runs in time range — trend unavailable",
                confidence="insufficient_data",
            )
            self.db.add(scorecard)
            await self.db.flush()
            return scorecard

        pass_rates = [r.pass_rate for r in runs if r.pass_rate is not None]
        overall = sum(pass_rates) / len(pass_rates) if pass_rates else None

        evaluator_breakdown: dict[str, list[float]] = {}
        for run in runs:
            for case in run.evaluator_results or []:
                for ev in case.get("evaluators") or []:
                    name = ev.get("name", "unknown")
                    score = ev.get("score")
                    if score is not None:
                        evaluator_breakdown.setdefault(name, []).append(float(score))

        dimensions = {
            name: {
                "average_score": sum(scores) / len(scores),
                "sample_count": len(scores),
                "methodology": "averaged from evaluation run case results",
            }
            for name, scores in evaluator_breakdown.items()
        }

        confidence = "high" if len(runs) >= 10 else ("medium" if len(runs) >= 3 else "low")

        scorecard = QualityScorecard(
            organization_id=org_id,
            scorecard_type="quality",
            time_range=time_range,
            overall_score=overall,
            dimensions=dimensions,
            formula="average(pass_rate) across quality evaluation runs; per-evaluator breakdown from case results",
            inputs={"run_count": len(runs), "case_count": sum(r.pass_count + r.fail_count for r in runs)},
            limitations=(
                "Quality scores depend on dataset coverage and evaluator methodology. "
                "LLM judge scores are subjective. Composite scores are explanatory, not absolute truth."
            ),
            confidence=confidence,
        )
        self.db.add(scorecard)
        await self.db.flush()
        return scorecard

    async def list_scorecards(self, org_id: uuid.UUID, limit: int = 20) -> list[QualityScorecard]:
        result = await self.db.execute(
            select(QualityScorecard)
            .where(QualityScorecard.organization_id == org_id)
            .order_by(QualityScorecard.computed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
