"""Region metadata management."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud import Region, RegionStatus
from app.services.metrics import record_region_status

DEFAULT_REGIONS = [
    {
        "name": "Local",
        "code": "local",
        "location": "Self-hosted deployment",
        "status": RegionStatus.ACTIVE,
        "capabilities": ["chat", "embeddings", "agents", "workflows", "governance"],
        "data_residency_zones": ["global"],
    },
]


class RegionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def seed_defaults(self) -> None:
        for spec in DEFAULT_REGIONS:
            existing = await self.db.execute(select(Region).where(Region.code == spec["code"]))
            if existing.scalar_one_or_none():
                continue
            region = Region(
                name=spec["name"],
                code=spec["code"],
                location=spec["location"],
                status=spec["status"],
                capabilities=list(spec["capabilities"]),
                data_residency_zones=list(spec["data_residency_zones"]),
            )
            self.db.add(region)
        await self.db.flush()

    async def list_regions(self, *, include_disabled: bool = False) -> list[Region]:
        q = select(Region).order_by(Region.code)
        if not include_disabled:
            q = q.where(Region.status != RegionStatus.DISABLED)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_by_code(self, code: str) -> Region | None:
        result = await self.db.execute(select(Region).where(Region.code == code))
        return result.scalar_one_or_none()

    async def get(self, region_id: uuid.UUID) -> Region | None:
        return await self.db.get(Region, region_id)

    async def create(
        self,
        *,
        name: str,
        code: str,
        location: str | None,
        capabilities: list[str] | None = None,
        data_residency_zones: list[str] | None = None,
    ) -> Region:
        region = Region(
            name=name,
            code=code.lower(),
            location=location,
            status=RegionStatus.ACTIVE,
            capabilities=capabilities or [],
            data_residency_zones=data_residency_zones or [],
        )
        self.db.add(region)
        await self.db.flush()
        record_region_status(region.code, region.status)
        return region

    async def update(
        self,
        region: Region,
        *,
        name: str | None = None,
        location: str | None = None,
        status: str | None = None,
        capabilities: list[str] | None = None,
        data_residency_zones: list[str] | None = None,
    ) -> Region:
        if name is not None:
            region.name = name
        if location is not None:
            region.location = location
        if status is not None:
            region.status = status
            record_region_status(region.code, status)
        if capabilities is not None:
            region.capabilities = capabilities
        if data_residency_zones is not None:
            region.data_residency_zones = data_residency_zones
        region.updated_at = datetime.now(UTC)
        await self.db.flush()
        return region

    def eligible_for_routing(self, region: Region) -> bool:
        return region.status in {RegionStatus.ACTIVE, RegionStatus.DEGRADED}

    def residency_matches(self, region: Region, policy: str) -> bool:
        """Check if region can satisfy a data residency policy.

        Self-hosted deployments only guarantee residency when regions are
        explicitly configured with matching zones. GLOBAL always matches.
        """
        if policy == "global":
            return True
        zones = {z.lower() for z in (region.data_residency_zones or [])}
        if policy == "eu_only":
            return bool(zones & {"eu", "eu_only", "europe"})
        if policy == "us_only":
            return bool(zones & {"us", "us_only", "north_america"})
        if policy == "india_only":
            return bool(zones & {"in", "india", "india_only"})
        return False
