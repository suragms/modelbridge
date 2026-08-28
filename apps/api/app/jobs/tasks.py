"""ARQ background tasks: provider health checks and data retention."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import delete, select

from app.config import get_settings
from app.db.base import async_session_factory
from app.models.audit import AuditLog
from app.models.job_run import JobRun
from app.models.provider import Provider
from app.models.request_log import CostRecord, RequestLog, UsageRecord
from app.services.health import HealthService

logger = structlog.get_logger()


async def _record_job_start(job_name: str) -> uuid.UUID:
    run_id = uuid.uuid4()
    async with async_session_factory() as db:
        db.add(JobRun(id=run_id, job_name=job_name, status="running"))
        await db.commit()
    return run_id


async def _record_job_finish(
    run_id: uuid.UUID,
    *,
    status: str,
    started: float,
    records: int | None = None,
    error: str | None = None,
    metadata: dict | None = None,
) -> None:
    async with async_session_factory() as db:
        run = await db.get(JobRun, run_id)
        if run:
            run.status = status
            run.completed_at = datetime.now(UTC)
            run.duration_ms = (time.time() - started) * 1000
            run.records_processed = records
            run.error_message = error
            run.metadata_ = metadata
            await db.commit()


async def provider_health_checks(ctx) -> dict:
    """Scheduled health checks for all enabled providers."""
    del ctx
    job_name = "provider_health_checks"
    run_id = await _record_job_start(job_name)
    started = time.time()
    checked = 0
    try:
        async with async_session_factory() as db:
            result = await db.execute(select(Provider).where(Provider.is_enabled == True))  # noqa: E712
            providers = result.scalars().all()
            health = HealthService(db)
            for provider in providers:
                try:
                    await health.check_provider(provider)
                    checked += 1
                except Exception as e:
                    logger.warning("health_check_failed", provider=str(provider.id), error=str(e))
            await db.commit()
        await _record_job_finish(run_id, status="completed", started=started, records=checked)
        return {"checked": checked}
    except Exception as e:
        await _record_job_finish(run_id, status="failed", started=started, error=str(e))
        raise


async def data_retention_cleanup(ctx) -> dict:
    """Delete expired request logs, usage, and cost records per retention settings."""
    del ctx
    settings = get_settings()
    job_name = "data_retention_cleanup"
    run_id = await _record_job_start(job_name)
    started = time.time()
    deleted = 0
    try:
        async with async_session_factory() as db:
            req_cutoff = datetime.now(UTC) - timedelta(days=settings.request_log_retention_days)
            audit_cutoff = datetime.now(UTC) - timedelta(days=settings.audit_log_retention_days)

            old_logs = await db.execute(
                select(RequestLog.request_id).where(RequestLog.created_at < req_cutoff)
            )
            old_ids = [r[0] for r in old_logs.all()]
            if old_ids:
                await db.execute(delete(UsageRecord).where(UsageRecord.request_id.in_(old_ids)))
                await db.execute(delete(CostRecord).where(CostRecord.request_id.in_(old_ids)))
                result = await db.execute(delete(RequestLog).where(RequestLog.request_id.in_(old_ids)))
                deleted += result.rowcount or 0

            audit_result = await db.execute(delete(AuditLog).where(AuditLog.created_at < audit_cutoff))
            deleted += audit_result.rowcount or 0
            await db.commit()

        await _record_job_finish(run_id, status="completed", started=started, records=deleted)
        logger.info("retention_cleanup", deleted=deleted)
        return {"deleted": deleted}
    except Exception as e:
        await _record_job_finish(run_id, status="failed", started=started, error=str(e))
        raise
