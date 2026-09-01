"""Background jobs for quality platform."""

from __future__ import annotations

import structlog
from sqlalchemy import select

from app.db.base import async_session_factory
from app.models.organization import Organization
from app.models.quality import PipelineStatus, QualityPipeline
from app.services.quality.pipelines import PipelineService
from app.services.quality.production import ProductionQualityService
from app.services.quality.scorecards import ScorecardService

logger = structlog.get_logger()


async def run_scheduled_quality_pipelines(ctx) -> dict:
    """Run pipelines with cron schedules."""
    ran = 0
    async with async_session_factory() as db:
        result = await db.execute(
            select(QualityPipeline).where(
                QualityPipeline.status == PipelineStatus.ACTIVE,
                QualityPipeline.schedule.isnot(None),
            )
        )
        pipelines = list(result.scalars().all())
        for pipeline in pipelines:
            try:
                await PipelineService(db).run(
                    pipeline,
                    org_id=pipeline.organization_id,
                    user_id=pipeline.created_by,
                    trigger="schedule",
                )
                ran += 1
            except Exception as e:
                logger.warning("quality_pipeline_failed", pipeline_id=str(pipeline.id), error=str(e))
        await db.commit()
    return {"pipelines_run": ran}


async def run_production_sampling(ctx) -> dict:
    """Sample production requests for orgs with sampling enabled."""
    sampled = 0
    async with async_session_factory() as db:
        orgs = await db.execute(select(Organization.id))
        for (org_id,) in orgs.all():
            try:
                svc = ProductionQualityService(db)
                config = await svc.get_or_create_config(org_id)
                if config.enabled:
                    samples = await svc.sample_requests(org_id, limit=20)
                    sampled += len(samples)
                    await svc.cleanup_expired(org_id)
            except Exception as e:
                logger.warning("production_sampling_failed", org_id=str(org_id), error=str(e))
        await db.commit()
    return {"samples_created": sampled}


async def aggregate_quality_trends(ctx) -> dict:
    """Compute scorecards for active organizations."""
    computed = 0
    async with async_session_factory() as db:
        orgs = await db.execute(select(Organization.id))
        for (org_id,) in orgs.all():
            try:
                await ScorecardService(db).compute_quality(org_id, "7d")
                await ScorecardService(db).compute_reliability(org_id, "7d")
                computed += 1
            except Exception as e:
                logger.warning("trend_aggregation_failed", org_id=str(org_id), error=str(e))
        await db.commit()
    return {"organizations_processed": computed}
