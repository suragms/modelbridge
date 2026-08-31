"""Event dispatch to subscribers."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform import (
    Automation,
    AutomationStatus,
    EventSubscription,
    PlatformEvent,
    SubscriptionTarget,
    WebhookEndpoint,
    WebhookStatus,
)
from app.services.platform.webhooks import WebhookService


class EventDispatcher:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def dispatch(self, event: PlatformEvent, data: dict | None = None) -> None:
        subs = await self.db.execute(
            select(EventSubscription).where(
                EventSubscription.organization_id == event.organization_id,
                EventSubscription.is_enabled == True,  # noqa: E712
            )
        )
        webhook_svc = WebhookService(self.db)

        for sub in subs.scalars().all():
            types = sub.event_types or []
            if event.event_type not in types and "*" not in types:
                continue

            if sub.target_type == SubscriptionTarget.WEBHOOK:
                webhook = await self.db.get(WebhookEndpoint, sub.target_id)
                if webhook and webhook.status == WebhookStatus.ACTIVE:
                    wh_types = webhook.event_types or []
                    if event.event_type in wh_types or "*" in wh_types:
                        delivery = await webhook_svc.queue_delivery(
                            organization_id=event.organization_id,
                            webhook=webhook,
                            event_id=event.id,
                        )
                        await self._enqueue_delivery(delivery.id)

        await self._trigger_automations(event)

    async def _enqueue_delivery(self, delivery_id: uuid.UUID) -> None:
        try:
            from app.services.agents.queue import get_arq_pool

            pool = await get_arq_pool()
            if pool:
                await pool.enqueue_job("deliver_webhook_job", str(delivery_id))
                return
        except Exception:
            pass
        try:
            from app.services.platform.delivery import DeliveryService

            await DeliveryService(self.db).deliver(delivery_id)
        except Exception:
            pass

    async def _trigger_automations(self, event: PlatformEvent) -> None:
        from app.services.platform.automations import AutomationService

        result = await self.db.execute(
            select(Automation).where(
                Automation.organization_id == event.organization_id,
                Automation.status == AutomationStatus.ACTIVE,
                Automation.trigger_type == "event",
            )
        )
        svc = AutomationService(self.db)
        for automation in result.scalars().all():
            cfg = automation.trigger_config or {}
            if cfg.get("event_type") in {event.event_type, "*"}:
                await svc.execute(automation, event_id=event.id)
