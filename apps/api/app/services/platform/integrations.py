"""Integration framework and GitHub adapter."""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.encryption import decrypt_secret, encrypt_secret
from app.models.platform import Integration, IntegrationStatus
from app.services.metrics import record_integration_request

GITHUB_EVENTS = frozenset({"push", "pull_request", "workflow_run"})


class IntegrationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        organization_id: uuid.UUID,
        provider: str,
        name: str,
        config: dict | None = None,
        created_by: uuid.UUID | None,
    ) -> Integration:
        integration = Integration(
            organization_id=organization_id,
            provider=provider,
            name=name,
            config=config or {},
            status=IntegrationStatus.DRAFT,
            created_by=created_by,
        )
        self.db.add(integration)
        await self.db.flush()
        return integration

    async def list_integrations(self, organization_id: uuid.UUID) -> list[Integration]:
        result = await self.db.execute(
            select(Integration)
            .where(Integration.organization_id == organization_id)
            .order_by(Integration.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, organization_id: uuid.UUID, integration_id: uuid.UUID) -> Integration | None:
        i = await self.db.get(Integration, integration_id)
        if not i or i.organization_id != organization_id:
            return None
        return i

    async def connect(
        self,
        integration: Integration,
        credential: str,
        *,
        verify: bool = True,
    ) -> Integration:
        if verify:
            ok = await self._verify(integration.provider, credential, integration.config)
            if not ok:
                integration.status = IntegrationStatus.ERROR
                integration.last_error = "Credential verification failed"
                await self.db.flush()
                raise ValueError("Integration credential verification failed")

        integration.credential_encrypted = encrypt_secret(credential)
        integration.status = IntegrationStatus.CONNECTED
        integration.last_sync_at = datetime.now(UTC)
        integration.last_error = None
        await self.db.flush()

        from app.services.platform.events import EventBus

        await EventBus(self.db).emit(
            organization_id=integration.organization_id,
            event_type="integration.connected",
            data={"integration_id": str(integration.id), "provider": integration.provider},
        )
        return integration

    async def disconnect(self, integration: Integration) -> Integration:
        integration.credential_encrypted = None
        integration.status = IntegrationStatus.DISABLED
        await self.db.flush()
        return integration

    async def _verify(self, provider: str, credential: str, config: dict) -> bool:
        if provider == "github":
            return await self._verify_github(credential)
        return bool(credential)

    async def _verify_github(self, token: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                )
            record_integration_request(provider="github", status="success" if resp.status_code == 200 else "failed")
            return resp.status_code == 200
        except httpx.HTTPError:
            record_integration_request(provider="github", status="failed")
            return False

    @staticmethod
    def verify_github_webhook(payload: bytes, signature: str, secret: str) -> bool:
        if not signature.startswith("sha256="):
            return False
        expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def handle_github_event(
        self,
        integration: Integration,
        event_name: str,
        payload: dict,
    ) -> dict:
        if event_name not in GITHUB_EVENTS:
            return {"status": "ignored", "event": event_name}

        from app.models.platform import Automation, AutomationStatus
        from app.services.platform.automations import AutomationService

        automations = await self.db.execute(
            select(Automation).where(
                Automation.organization_id == integration.organization_id,
                Automation.status == AutomationStatus.ACTIVE,
                Automation.trigger_type == "github_event",
            )
        )
        triggered = 0
        svc = AutomationService(self.db)
        for automation in automations.scalars().all():
            if automation.trigger_type == "github_event":
                cfg = automation.trigger_config or {}
                if cfg.get("event") in {event_name, "*"}:
                    await svc.execute(
                        automation,
                        context={"github_event": event_name, "payload_ref": payload.get("repository", {}).get("full_name")},
                    )
                    triggered += 1

        integration.last_sync_at = datetime.now(UTC)
        await self.db.flush()
        return {"status": "processed", "event": event_name, "automations_triggered": triggered}
