"""Anomaly detection using statistical deviation from historical baseline."""

from __future__ import annotations

import statistics
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import AnomalySeverity, AnomalyStatus, IntelligenceAnomaly
from app.models.request_log import FAILED_STATUSES, RequestLog
from app.services.intelligence.data_quality import MIN_SAMPLES_ANOMALY, assess_quality
from app.services.metrics import record_anomaly_detected


class AnomalyService:
    ZSCORE_THRESHOLD = 2.5

    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect(self, organization_id: uuid.UUID, *, days: int = 14) -> dict:
        end = datetime.now(UTC)
        start = end - timedelta(days=days)
        trunc = func.date_trunc("day", RequestLog.created_at)

        latency_q = await self.db.execute(
            select(trunc, func.avg(RequestLog.latency_ms))
            .where(
                RequestLog.organization_id == organization_id,
                RequestLog.created_at >= start,
                RequestLog.created_at <= end,
                RequestLog.status.notin_(list(FAILED_STATUSES)),
            )
            .group_by(trunc)
            .order_by(trunc)
        )
        error_q = await self.db.execute(
            select(trunc, func.count(RequestLog.id))
            .where(
                RequestLog.organization_id == organization_id,
                RequestLog.created_at >= start,
                RequestLog.created_at <= end,
                RequestLog.status.in_(list(FAILED_STATUSES)),
            )
            .group_by(trunc)
            .order_by(trunc)
        )

        latency_series = [float(r[1]) for r in latency_q.all() if r[1] is not None]
        error_series = [float(r[1]) for r in error_q.all()]

        quality = assess_quality(
            sample_size=max(len(latency_series), len(error_series)),
            min_samples=MIN_SAMPLES_ANOMALY,
        )

        if quality.status == "insufficient_data":
            return {
                "status": "insufficient_data",
                "data_quality": quality.to_dict(),
                "anomalies": [],
            }

        detected: list[IntelligenceAnomaly] = []
        for metric, series in [("latency_ms", latency_series), ("error_count", error_series)]:
            if len(series) < MIN_SAMPLES_ANOMALY:
                continue
            anomaly = self._check_series(organization_id, metric, series)
            if anomaly:
                self.db.add(anomaly)
                detected.append(anomaly)
                record_anomaly_detected(severity=anomaly.severity)

        await self.db.flush()
        return {
            "status": "ok",
            "data_quality": quality.to_dict(),
            "anomalies_detected": len(detected),
            "anomalies": [self._serialize(a) for a in detected],
        }

    def _check_series(
        self, organization_id: uuid.UUID, metric: str, series: list[float]
    ) -> IntelligenceAnomaly | None:
        if len(series) < 3:
            return None
        baseline = series[:-1]
        current = series[-1]
        mean = statistics.mean(baseline)
        stdev = statistics.stdev(baseline) if len(baseline) > 1 else 0
        if stdev == 0:
            return None
        z = abs(current - mean) / stdev
        if z < self.ZSCORE_THRESHOLD:
            return None

        severity = self._severity(z, metric, current, mean)
        return IntelligenceAnomaly(
            organization_id=organization_id,
            metric=metric,
            observed_value=current,
            expected_min=mean - 2 * stdev,
            expected_max=mean + 2 * stdev,
            deviation=z,
            severity=severity,
            status=AnomalyStatus.OPEN,
            evidence={
                "method": "z_score",
                "baseline_mean": round(mean, 2),
                "baseline_stdev": round(stdev, 2),
                "z_score": round(z, 2),
                "sample_days": len(series),
            },
        )

    def _severity(self, z: float, metric: str, current: float, mean: float) -> str:
        if z >= 4:
            return AnomalySeverity.CRITICAL
        if z >= 3.5:
            return AnomalySeverity.HIGH
        if z >= 3:
            return AnomalySeverity.MEDIUM
        if metric == "error_count" and current > mean * 2:
            return AnomalySeverity.HIGH
        return AnomalySeverity.LOW

    async def list_anomalies(
        self, organization_id: uuid.UUID, *, status: str | None = None, limit: int = 50
    ) -> list[dict]:
        q = (
            select(IntelligenceAnomaly)
            .where(IntelligenceAnomaly.organization_id == organization_id)
            .order_by(IntelligenceAnomaly.detected_at.desc())
            .limit(limit)
        )
        if status:
            q = q.where(IntelligenceAnomaly.status == status)
        result = await self.db.execute(q)
        return [self._serialize(a) for a in result.scalars().all()]

    def _serialize(self, a: IntelligenceAnomaly) -> dict:
        return {
            "id": str(a.id),
            "metric": a.metric,
            "dimension": a.dimension,
            "observed_value": a.observed_value,
            "expected_min": a.expected_min,
            "expected_max": a.expected_max,
            "deviation": a.deviation,
            "severity": a.severity,
            "status": a.status,
            "evidence": a.evidence,
            "detected_at": a.detected_at.isoformat(),
        }
