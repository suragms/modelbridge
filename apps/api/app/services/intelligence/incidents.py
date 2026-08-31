"""Incident intelligence with labeled correlations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud import CloudIncident
from app.models.enterprise import ConfigurationDeployment, DeploymentStatus
from app.models.request_log import FAILED_STATUSES, RequestLog


class IncidentIntelligenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_incident(self, organization_id: uuid.UUID, incident_id: uuid.UUID) -> dict:
        incident = await self.db.get(CloudIncident, incident_id)
        if not incident or (incident.organization_id and incident.organization_id != organization_id):
            return {"status": "not_found"}

        window_start = incident.started_at - timedelta(hours=2)
        window_end = incident.started_at + timedelta(hours=2)

        errors = await self.db.execute(
            select(RequestLog.provider, RequestLog.error_type, RequestLog.created_at)
            .where(
                RequestLog.organization_id == organization_id,
                RequestLog.status.in_(list(FAILED_STATUSES)),
                RequestLog.created_at >= window_start,
                RequestLog.created_at <= window_end,
            )
            .limit(20)
        )
        error_rows = errors.all()

        deployments = await self.db.execute(
            select(ConfigurationDeployment)
            .where(
                ConfigurationDeployment.organization_id == organization_id,
                ConfigurationDeployment.created_at >= window_start,
                ConfigurationDeployment.created_at <= window_end,
            )
            .order_by(ConfigurationDeployment.created_at.desc())
            .limit(5)
        )
        deploy_rows = deployments.scalars().all()

        correlations = []
        if error_rows:
            providers = {r[0] for r in error_rows}
            correlations.append({
                "type": "observed",
                "signal": "errors",
                "detail": f"{len(error_rows)} errors from providers: {', '.join(providers)}",
                "time_window": {"start": window_start.isoformat(), "end": window_end.isoformat()},
            })

        if deploy_rows:
            correlations.append({
                "type": "correlated",
                "signal": "deployment",
                "detail": f"{len(deploy_rows)} configuration deployment(s) in the time window.",
                "deployments": [str(d.id) for d in deploy_rows],
            })
            if error_rows:
                correlations.append({
                    "type": "hypothesis",
                    "signal": "latency_or_errors",
                    "detail": (
                        "Errors occurred within the observed time window around a configuration deployment. "
                        "This is a hypothesis — not confirmed root cause."
                    ),
                    "evidence": "Temporal correlation only.",
                })

        return {
            "status": "ok",
            "incident_id": str(incident_id),
            "title": incident.title,
            "correlations": correlations,
            "disclaimer": "Hypotheses are not confirmed root causes.",
        }
