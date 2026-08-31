"""Background jobs for webhook delivery and retries."""

from __future__ import annotations

import uuid

import structlog

from app.db.base import async_session_factory
from app.services.platform.delivery import DeliveryService

logger = structlog.get_logger()


async def deliver_webhook_job(ctx, delivery_id: str) -> dict:
    """Deliver a single webhook payload."""
    async with async_session_factory() as db:
        try:
            delivery = await DeliveryService(db).deliver(uuid.UUID(delivery_id))
            await db.commit()
            return {"delivery_id": delivery_id, "status": delivery.status}
        except Exception as e:
            await db.rollback()
            logger.error("webhook_delivery_job_failed", delivery_id=delivery_id, error=str(e))
            raise


async def process_webhook_retries(ctx) -> dict:
    """Process pending webhook retries."""
    async with async_session_factory() as db:
        try:
            count = await DeliveryService(db).process_retries()
            await db.commit()
            return {"retried": count}
        except Exception as e:
            await db.rollback()
            logger.error("webhook_retry_job_failed", error=str(e))
            raise
