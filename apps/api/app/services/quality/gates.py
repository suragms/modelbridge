"""Quality gates, alerts, and incidents."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quality import (
    QualityAlert,
    QualityAlertStatus,
    QualityGate,
    QualityIncident,
    QualityIncidentStatus,
    QualityRegressionComparison,
    RegressionStatus,
)
from app.models.studio import StudioDeployment, StudioDeploymentStatus
from app.services.metrics import record_quality_alert, record_quality_gate_failure
from app.services.platform.events import EventBus


class GateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        org_id: uuid.UUID,
        name: str,
        pipeline_id: uuid.UUID,
        min_pass_rate: float = 0.9,
        min_safety_score: float | None = None,
        max_regression_delta: float | None = None,
        block_deployment: bool = True,
    ) -> QualityGate:
        gate = QualityGate(
            organization_id=org_id,
            name=name,
            pipeline_id=pipeline_id,
            min_pass_rate=min_pass_rate,
            min_safety_score=min_safety_score,
            max_regression_delta=max_regression_delta,
            block_deployment=block_deployment,
        )
        self.db.add(gate)
        await self.db.flush()
        return gate

    async def list_gates(self, org_id: uuid.UUID) -> list[QualityGate]:
        result = await self.db.execute(
            select(QualityGate)
            .where(QualityGate.organization_id == org_id, QualityGate.enabled.is_(True))
            .order_by(QualityGate.created_at.desc())
        )
        return list(result.scalars().all())

    async def evaluate_for_deployment(
        self,
        *,
        org_id: uuid.UUID,
        deployment: StudioDeployment,
        run_pass_rate: float | None,
        pipeline_service,
        user_id: uuid.UUID | None,
    ) -> dict:
        gates = await self.list_gates(org_id)
        if not gates:
            return {"passed": True, "checks": [], "message": "No quality gates configured"}

        checks: list[dict] = []
        all_passed = True

        for gate in gates:
            passed = True
            detail = "Gate check passed"
            if run_pass_rate is not None and run_pass_rate < gate.min_pass_rate:
                passed = False
                detail = f"Pass rate {run_pass_rate:.2f} below threshold {gate.min_pass_rate}"

            checks.append({
                "gate_id": str(gate.id),
                "gate_name": gate.name,
                "passed": passed,
                "detail": detail,
                "methodology": f"Pipeline pass_rate >= {gate.min_pass_rate}",
            })

            if not passed:
                all_passed = False
                record_quality_gate_failure()
                await EventBus(self.db).emit(
                    organization_id=org_id,
                    event_type="quality.gate.failed",
                    data={"gate_id": str(gate.id), "deployment_id": str(deployment.id), "status": "failed"},
                    source="quality",
                )
                if gate.block_deployment:
                    from app.services.studio.deployments import DeploymentService

                    await DeploymentService(self.db).reject(
                        deployment, f"Quality gate failed: {gate.name} — {detail}"
                    )
                    await AlertService(self.db).create_gate_failure(
                        org_id=org_id, gate_id=gate.id, deployment_id=deployment.id, detail=detail
                    )

        state = deployment.pipeline_state or {}
        deployment.pipeline_state = {**state, "quality_checks": checks, "quality_passed": all_passed}
        await self.db.flush()
        return {"passed": all_passed, "checks": checks}


class AlertService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_threshold_violation(
        self,
        *,
        org_id: uuid.UUID,
        run_id: uuid.UUID,
        pass_rate: float,
        threshold: float,
    ) -> QualityAlert:
        alert = QualityAlert(
            organization_id=org_id,
            alert_type="threshold_violation",
            title=f"Evaluation pass rate {pass_rate:.2f} below threshold {threshold:.2f}",
            evidence={"pass_rate": pass_rate, "threshold": threshold, "run_id": str(run_id)},
            run_id=run_id,
            status=QualityAlertStatus.OPEN,
        )
        self.db.add(alert)
        record_quality_alert(status="open")
        await EventBus(self.db).emit(
            organization_id=org_id,
            event_type="quality.threshold.violated",
            data={"execution_id": str(run_id), "status": "open"},
            source="quality",
        )
        await self.db.flush()
        return alert

    async def create_regression_alert(
        self,
        *,
        org_id: uuid.UUID,
        comparison: QualityRegressionComparison,
    ) -> QualityAlert:
        alert = QualityAlert(
            organization_id=org_id,
            alert_type="quality_regression",
            title=f"Regression detected: {comparison.comparison_type}",
            evidence={
                "comparison_id": str(comparison.id),
                "differences": comparison.differences,
                "metrics": comparison.metrics,
            },
            status=QualityAlertStatus.OPEN,
        )
        self.db.add(alert)
        record_quality_alert(status="open")
        await self._maybe_create_incident(org_id, alert, comparison)
        await self.db.flush()
        return alert

    async def create_gate_failure(
        self,
        *,
        org_id: uuid.UUID,
        gate_id: uuid.UUID,
        deployment_id: uuid.UUID,
        detail: str,
    ) -> QualityAlert:
        alert = QualityAlert(
            organization_id=org_id,
            alert_type="gate_failure",
            title="Deployment blocked by quality gate",
            evidence={"gate_id": str(gate_id), "deployment_id": str(deployment_id), "detail": detail},
            gate_id=gate_id,
            status=QualityAlertStatus.OPEN,
        )
        self.db.add(alert)
        record_quality_alert(status="open")
        await self.db.flush()
        return alert

    async def list_alerts(self, org_id: uuid.UUID, limit: int = 50) -> list[QualityAlert]:
        result = await self.db.execute(
            select(QualityAlert)
            .where(QualityAlert.organization_id == org_id)
            .order_by(QualityAlert.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _maybe_create_incident(
        self,
        org_id: uuid.UUID,
        alert: QualityAlert,
        comparison: QualityRegressionComparison,
    ) -> None:
        regressions = (comparison.differences or {}).get("regressions") or []
        if "quality_drop" in regressions:
            incident = QualityIncident(
                organization_id=org_id,
                alert_id=alert.id,
                title=f"Quality regression: {comparison.comparison_type}",
                status=QualityIncidentStatus.OPEN,
                affected_version=comparison.candidate_label,
                evidence={"comparison_id": str(comparison.id), "metrics": comparison.metrics},
            )
            self.db.add(incident)

    async def list_incidents(self, org_id: uuid.UUID, limit: int = 50) -> list[QualityIncident]:
        result = await self.db.execute(
            select(QualityIncident)
            .where(QualityIncident.organization_id == org_id)
            .order_by(QualityIncident.detected_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
