"""Webhook endpoint management and delivery orchestration."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform import (
    DeliveryStatus,
    EventSubscription,
    SubscriptionTarget,
    WebhookDelivery,
    WebhookEndpoint,
    WebhookStatus,
)
from app.services.platform.events import EventCatalog
from app.services.platform.signing import encrypt_webhook_secret, generate_webhook_secret
from app.services.platform.ssrf import SSRFError, validate_webhook_url


class WebhookService:
    MAX_ATTEMPTS = 5

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        organization_id: uuid.UUID,
        name: str,
        url: str,
        event_types: list[str],
        created_by: uuid.UUID | None,
    ) -> tuple[WebhookEndpoint, str]:
        for et in event_types:
            if not EventCatalog.is_valid(et):
                raise ValueError(f"Invalid event type: {et}")

        validated_url = validate_webhook_url(url)
        secret = generate_webhook_secret()
        endpoint = WebhookEndpoint(
            organization_id=organization_id,
            name=name,
            url=validated_url,
            event_types=event_types,
            status=WebhookStatus.ACTIVE,
            secret_encrypted=encrypt_webhook_secret(secret),
            secret_prefix=secret[:12] + "...",
            created_by=created_by,
        )
        self.db.add(endpoint)
        await self.db.flush()

        self.db.add(
            EventSubscription(
                organization_id=organization_id,
                event_types=event_types,
                target_type=SubscriptionTarget.WEBHOOK,
                target_id=endpoint.id,
            )
        )
        await self.db.flush()
        return endpoint, secret

    async def list_endpoints(self, organization_id: uuid.UUID) -> list[WebhookEndpoint]:
        result = await self.db.execute(
            select(WebhookEndpoint)
            .where(WebhookEndpoint.organization_id == organization_id)
            .order_by(WebhookEndpoint.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, organization_id: uuid.UUID, webhook_id: uuid.UUID) -> WebhookEndpoint | None:
        wh = await self.db.get(WebhookEndpoint, webhook_id)
        if not wh or wh.organization_id != organization_id:
            return None
        return wh

    async def update(
        self,
        webhook: WebhookEndpoint,
        *,
        name: str | None = None,
        url: str | None = None,
        event_types: list[str] | None = None,
        status: str | None = None,
    ) -> WebhookEndpoint:
        if url is not None:
            webhook.url = validate_webhook_url(url)
        if name is not None:
            webhook.name = name
        if event_types is not None:
            for et in event_types:
                if not EventCatalog.is_valid(et):
                    raise ValueError(f"Invalid event type: {et}")
            webhook.event_types = event_types
        if status is not None:
            webhook.status = status
        webhook.updated_at = datetime.now(UTC)
        await self.db.flush()
        return webhook

    async def delete(self, webhook: WebhookEndpoint) -> None:
        webhook.status = WebhookStatus.DISABLED
        await self.db.flush()

    async def rotate_secret(self, webhook: WebhookEndpoint) -> str:
        secret = generate_webhook_secret()
        webhook.secret_encrypted = encrypt_webhook_secret(secret)
        webhook.secret_prefix = secret[:12] + "..."
        webhook.updated_at = datetime.now(UTC)
        await self.db.flush()
        return secret

    async def queue_delivery(
        self,
        *,
        organization_id: uuid.UUID,
        webhook: WebhookEndpoint,
        event_id: uuid.UUID,
    ) -> WebhookDelivery:
        idempotency_key = f"{webhook.id}:{event_id}"
        existing = await self.db.execute(
            select(WebhookDelivery).where(WebhookDelivery.idempotency_key == idempotency_key)
        )
        found = existing.scalar_one_or_none()
        if found:
            return found

        delivery = WebhookDelivery(
            organization_id=organization_id,
            webhook_id=webhook.id,
            event_id=event_id,
            status=DeliveryStatus.PENDING,
            max_attempts=self.MAX_ATTEMPTS,
            idempotency_key=idempotency_key,
        )
        self.db.add(delivery)
        await self.db.flush()
        return delivery

    async def list_deliveries(
        self, organization_id: uuid.UUID, webhook_id: uuid.UUID, *, limit: int = 50
    ) -> list[WebhookDelivery]:
        result = await self.db.execute(
            select(WebhookDelivery)
            .where(
                WebhookDelivery.organization_id == organization_id,
                WebhookDelivery.webhook_id == webhook_id,
            )
            .order_by(WebhookDelivery.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_delivery(
        self, organization_id: uuid.UUID, delivery_id: uuid.UUID
    ) -> WebhookDelivery | None:
        d = await self.db.get(WebhookDelivery, delivery_id)
        if not d or d.organization_id != organization_id:
            return None
        return d
