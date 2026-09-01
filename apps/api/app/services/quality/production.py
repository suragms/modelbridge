"""Production sampling and quality signal evaluation."""

from __future__ import annotations

import hashlib
import random
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.quality import QualityProductionConfig, QualityProductionSample
from app.models.request_log import RequestLog, SUCCESS_STATUSES


REDACTED = "[REDACTED]"


class ProductionQualityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_config(self, org_id: uuid.UUID) -> QualityProductionConfig:
        result = await self.db.execute(
            select(QualityProductionConfig).where(QualityProductionConfig.organization_id == org_id)
        )
        config = result.scalar_one_or_none()
        if config:
            return config
        config = QualityProductionConfig(
            organization_id=org_id,
            enabled=False,
            sampling_rate=0.01,
            redaction_policy={"strip_content": True},
            retention_days=30,
        )
        self.db.add(config)
        await self.db.flush()
        return config

    async def update_config(
        self,
        org_id: uuid.UUID,
        *,
        enabled: bool | None = None,
        sampling_rate: float | None = None,
        sampling_rules: dict | None = None,
        redaction_policy: dict | None = None,
        retention_days: int | None = None,
        pipeline_id: uuid.UUID | None = None,
    ) -> QualityProductionConfig:
        config = await self.get_or_create_config(org_id)
        if enabled is not None:
            config.enabled = enabled
        if sampling_rate is not None:
            config.sampling_rate = min(max(sampling_rate, 0.0), 1.0)
        if sampling_rules is not None:
            config.sampling_rules = sampling_rules
        if redaction_policy is not None:
            config.redaction_policy = redaction_policy
        if retention_days is not None:
            config.retention_days = retention_days
        if pipeline_id is not None:
            config.pipeline_id = pipeline_id
        config.updated_at = datetime.now(UTC)
        await self.db.flush()
        return config

    async def sample_requests(self, org_id: uuid.UUID, limit: int = 100) -> list[QualityProductionSample]:
        config = await self.get_or_create_config(org_id)
        if not config.enabled:
            return []

        org = await self.db.get(Organization, org_id)
        if not org:
            return []

        cutoff = datetime.now(UTC) - timedelta(hours=24)
        result = await self.db.execute(
            select(RequestLog)
            .where(
                RequestLog.organization_id == org_id,
                RequestLog.created_at >= cutoff,
            )
            .order_by(RequestLog.created_at.desc())
            .limit(limit * 10)
        )
        logs = list(result.scalars().all())
        samples: list[QualityProductionSample] = []

        for log in logs:
            if random.random() > config.sampling_rate:
                continue
            if len(samples) >= limit:
                break

            redacted = self._redact_metadata(log, config.redaction_policy or {})
            signals = {
                "format_compliance": log.status in SUCCESS_STATUSES,
                "latency_ms": log.latency_ms,
                "error_rate_signal": log.status not in SUCCESS_STATUSES,
                "method": "request_log_metadata",
                "limitations": "Production sampling uses request metadata only; prompt content is not stored",
            }

            sample = QualityProductionSample(
                organization_id=org_id,
                request_id=self._hash_request_id(log.request_id),
                model=log.model,
                provider=log.provider,
                latency_ms=log.latency_ms,
                status=log.status,
                redacted_metadata=redacted,
                quality_signals=signals,
            )
            self.db.add(sample)
            samples.append(sample)

        await self.db.flush()
        return samples

    async def cleanup_expired(self, org_id: uuid.UUID) -> int:
        config = await self.get_or_create_config(org_id)
        cutoff = datetime.now(UTC) - timedelta(days=config.retention_days)
        result = await self.db.execute(
            delete(QualityProductionSample).where(
                QualityProductionSample.organization_id == org_id,
                QualityProductionSample.evaluated_at < cutoff,
            )
        )
        return result.rowcount or 0

    async def list_samples(self, org_id: uuid.UUID, limit: int = 50) -> list[QualityProductionSample]:
        result = await self.db.execute(
            select(QualityProductionSample)
            .where(QualityProductionSample.organization_id == org_id)
            .order_by(QualityProductionSample.evaluated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    def _redact_metadata(self, log: RequestLog, policy: dict) -> dict:
        data = {
            "model": log.model,
            "provider": log.provider,
            "status": log.status,
            "latency_ms": log.latency_ms,
            "error_code": log.error_code,
            "request_type": log.request_type,
        }
        if policy.get("strip_content"):
            data["content"] = REDACTED
        if log.error and policy.get("strip_errors"):
            data["error"] = REDACTED
        else:
            data["error"] = (log.error or "")[:200] if log.error else None
        return data

    def _hash_request_id(self, request_id: str) -> str:
        return hashlib.sha256(request_id.encode()).hexdigest()[:32]
