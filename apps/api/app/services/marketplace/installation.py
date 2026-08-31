"""Marketplace installation with history and rollback."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.extension import ExtensionInstallation, ExtensionPackageVersion, InstallationStatus
from app.models.marketplace import MarketplaceAnalyticsEvent, MarketplaceInstallHistory, MarketplaceItem
from app.services.extensions.lifecycle import ExtensionLifecycleError, ExtensionLifecycleService
from app.services.metrics import record_marketplace_installation


class MarketplaceInstallService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.lifecycle = ExtensionLifecycleService(db)

    async def install(
        self,
        item: MarketplaceItem,
        *,
        org_id: uuid.UUID,
        user_id: uuid.UUID | None,
        approved_permissions: list[str],
        version_id: uuid.UUID | None = None,
        enable: bool = True,
        config: dict | None = None,
    ) -> tuple[ExtensionInstallation, MarketplaceInstallHistory]:
        target_version_id = version_id or item.current_version_id
        if not target_version_id:
            raise ValueError("No version available for installation")

        await self.lifecycle.validate_install(target_version_id, approved_permissions=approved_permissions)

        try:
            inst = await self.lifecycle.install(
                org_id,
                target_version_id,
                user_id=user_id,
                approved_permissions=approved_permissions,
                config=config,
            )
            if enable:
                inst = await self.lifecycle.enable(inst, user_id=user_id)
        except ExtensionLifecycleError as e:
            raise ValueError(f"{e.code}: {e}") from e

        history = MarketplaceInstallHistory(
            item_id=item.id,
            version_id=target_version_id,
            installation_id=inst.id,
            organization_id=org_id,
            action="install",
            installed_by=user_id,
            status="completed",
        )
        item.install_count += 1
        self.db.add(history)
        self.db.add(
            MarketplaceAnalyticsEvent(
                item_id=item.id,
                event_type="install",
                organization_id=org_id,
                event_metadata={"version_id": str(target_version_id)},
            )
        )
        record_marketplace_installation(content_type=item.content_type)
        await self.db.flush()
        return inst, history

    async def update(
        self,
        item: MarketplaceItem,
        installation: ExtensionInstallation,
        new_version_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None,
        approved_permissions: list[str],
    ) -> MarketplaceInstallHistory:
        await self.lifecycle.validate_install(new_version_id, approved_permissions=approved_permissions)
        previous_version_id = installation.package_version_id

        installation.previous_version_id = previous_version_id
        installation.package_version_id = new_version_id
        installation.updated_at = datetime.now(UTC)

        history = MarketplaceInstallHistory(
            item_id=item.id,
            version_id=new_version_id,
            installation_id=installation.id,
            organization_id=installation.organization_id,
            action="update",
            previous_version_id=previous_version_id,
            installed_by=user_id,
            status="completed",
        )
        self.db.add(history)
        self.db.add(
            MarketplaceAnalyticsEvent(
                item_id=item.id,
                event_type="update",
                organization_id=installation.organization_id,
            )
        )
        await self.db.flush()
        return history

    async def rollback(
        self,
        item: MarketplaceItem,
        installation: ExtensionInstallation,
        *,
        user_id: uuid.UUID | None,
        reason: str | None = None,
    ) -> MarketplaceInstallHistory | None:
        if not installation.previous_version_id:
            return None

        prev_id = installation.previous_version_id
        current_id = installation.package_version_id
        installation.package_version_id = prev_id
        installation.previous_version_id = None
        installation.updated_at = datetime.now(UTC)

        history = MarketplaceInstallHistory(
            item_id=item.id,
            version_id=prev_id,
            installation_id=installation.id,
            organization_id=installation.organization_id,
            action="rollback",
            previous_version_id=current_id,
            installed_by=user_id,
            status="completed",
            reason=reason,
        )
        self.db.add(history)
        await self.db.flush()
        return history

    async def install_history(
        self, org_id: uuid.UUID, item_id: uuid.UUID | None = None, limit: int = 50
    ) -> list[MarketplaceInstallHistory]:
        q = (
            select(MarketplaceInstallHistory)
            .where(MarketplaceInstallHistory.organization_id == org_id)
            .order_by(MarketplaceInstallHistory.created_at.desc())
            .limit(min(limit, 100))
        )
        if item_id:
            q = q.where(MarketplaceInstallHistory.item_id == item_id)
        result = await self.db.execute(q)
        return list(result.scalars().all())
