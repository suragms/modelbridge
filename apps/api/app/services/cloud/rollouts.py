"""Multi-region configuration rollout with verification."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud import ConfigurationRollout, RolloutStatus, ScopedConfiguration
from app.services.metrics import record_configuration_rollout


class RolloutService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_rollouts(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        region_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[ConfigurationRollout]:
        q = select(ConfigurationRollout).order_by(ConfigurationRollout.created_at.desc()).limit(limit)
        if organization_id:
            q = q.where(ConfigurationRollout.organization_id == organization_id)
        if region_id:
            q = q.where(ConfigurationRollout.region_id == region_id)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def create_rollout(
        self,
        *,
        organization_id: uuid.UUID | None,
        scoped_configuration: ScopedConfiguration | None,
        configuration_version_id: uuid.UUID | None,
        region_id: uuid.UUID | None,
        configuration_version: int,
        deployed_by: uuid.UUID | None,
    ) -> ConfigurationRollout:
        rollout = ConfigurationRollout(
            organization_id=organization_id,
            scoped_configuration_id=scoped_configuration.id if scoped_configuration else None,
            configuration_version_id=configuration_version_id,
            region_id=region_id,
            configuration_version=configuration_version,
            status=RolloutStatus.DEPLOYING,
            deployed_by=deployed_by,
        )
        self.db.add(rollout)
        await self.db.flush()

        verified = await self._verify(rollout, scoped_configuration)
        if verified:
            rollout.status = RolloutStatus.SUCCESS
            rollout.verified_at = datetime.now(UTC)
            rollout.completed_at = datetime.now(UTC)
        else:
            rollout.status = RolloutStatus.FAILED
            rollout.error_message = "Verification failed — target region or configuration unavailable"
            rollout.completed_at = datetime.now(UTC)

        record_configuration_rollout(rollout.status)
        await self.db.flush()
        return rollout

    async def _verify(
        self,
        rollout: ConfigurationRollout,
        scoped_configuration: ScopedConfiguration | None,
    ) -> bool:
        if scoped_configuration and not scoped_configuration.is_active:
            return False
        if rollout.region_id:
            from app.models.cloud import Region, RegionStatus

            region = await self.db.get(Region, rollout.region_id)
            if not region or region.status == RegionStatus.DISABLED:
                return False
        return True
