"""Webhook HTTP delivery with retries."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform import DeliveryStatus, PlatformEvent, WebhookDelivery, WebhookEndpoint, WebhookStatus
from app.services.metrics import record_webhook_delivery, record_webhook_retry
from app.services.platform.events import EventBus
from app.services.platform.signing import decrypt_webhook_secret, sign_payload
from app.services.platform.webhooks import WebhookService

RETRY_DELAYS = [60, 300, 900, 3600, 7200]


class DeliveryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.webhooks = WebhookService(db)
        self.events = EventBus(db)

    async def deliver(self, delivery_id: uuid.UUID) -> WebhookDelivery:
        delivery = await self.db.get(WebhookDelivery, delivery_id)
        if not delivery:
            raise ValueError("Delivery not found")
        if delivery.status == DeliveryStatus.DELIVERED:
            return delivery

        webhook = await self.db.get(WebhookEndpoint, delivery.webhook_id)
        event = await self.db.get(PlatformEvent, delivery.event_id)
        if not webhook or not event or webhook.status != WebhookStatus.ACTIVE:
            delivery.status = DeliveryStatus.FAILED
            delivery.failure_category = "webhook_inactive"
            await self.db.flush()
            return delivery

        delivery.status = DeliveryStatus.DELIVERING
        delivery.attempt_count += 1
        delivery.last_attempt_at = datetime.now(UTC)
        await self.db.flush()

        envelope = self.events.envelope(event, event.payload_metadata)
        payload = json.dumps(envelope).encode()
        secret = decrypt_webhook_secret(webhook.secret_encrypted)
        signature = sign_payload(secret, payload)

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
                resp = await client.post(
                    webhook.url,
                    content=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-ModelBridge-Signature": signature,
                        "X-ModelBridge-Event-Id": str(event.id),
                        "X-ModelBridge-Event-Type": event.event_type,
                        "User-Agent": "ModelBridge-Webhooks/1.0",
                    },
                )
            delivery.response_status = resp.status_code
            if 200 <= resp.status_code < 300:
                delivery.status = DeliveryStatus.DELIVERED
                delivery.completed_at = datetime.now(UTC)
                record_webhook_delivery(status="delivered")
            else:
                await self._handle_failure(delivery, f"http_{resp.status_code}")
        except httpx.TimeoutException:
            await self._handle_failure(delivery, "timeout")
        except httpx.RequestError:
            await self._handle_failure(delivery, "network_error")

        await self.db.flush()
        return delivery

    async def _handle_failure(self, delivery: WebhookDelivery, category: str) -> None:
        delivery.failure_category = category
        if delivery.attempt_count >= delivery.max_attempts:
            delivery.status = DeliveryStatus.FAILED
            record_webhook_delivery(status="failed")
        else:
            delay = RETRY_DELAYS[min(delivery.attempt_count - 1, len(RETRY_DELAYS) - 1)]
            delivery.status = DeliveryStatus.RETRYING
            delivery.next_retry_at = datetime.now(UTC) + timedelta(seconds=delay)
            record_webhook_retry()
            record_webhook_delivery(status="retrying")

    async def process_retries(self) -> int:
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(WebhookDelivery).where(
                WebhookDelivery.status == DeliveryStatus.RETRYING,
                WebhookDelivery.next_retry_at <= now,
            ).limit(50)
        )
        count = 0
        for delivery in result.scalars().all():
            await self.deliver(delivery.id)
            count += 1
        return count

    async def manual_retry(self, organization_id: uuid.UUID, delivery_id: uuid.UUID) -> WebhookDelivery:
        delivery = await self.webhooks.get_delivery(organization_id, delivery_id)
        if not delivery:
            raise ValueError("Delivery not found")
        if delivery.status == DeliveryStatus.DELIVERED:
            return delivery
        delivery.status = DeliveryStatus.PENDING
        delivery.next_retry_at = None
        await self.db.flush()
        return await self.deliver(delivery.id)
