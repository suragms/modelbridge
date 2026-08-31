"""Background intelligence analysis jobs."""

from __future__ import annotations

import structlog

from app.db.base import async_session_factory
from app.services.intelligence.engine import IntelligenceEngine
from app.models.organization import Organization
from sqlalchemy import select

logger = structlog.get_logger()


async def run_intelligence_analysis(ctx) -> dict:
    """Daily intelligence analysis for all organizations."""
    processed = 0
    errors = 0
    async with async_session_factory() as db:
        orgs = await db.execute(select(Organization.id))
        for (org_id,) in orgs.all():
            try:
                engine = IntelligenceEngine(db)
                await engine.run_analysis(org_id, job_type="full")
                processed += 1
            except Exception as e:
                errors += 1
                logger.warning("intelligence_job_failed", org_id=str(org_id), error=str(e))
        await db.commit()
    return {"processed": processed, "errors": errors}
