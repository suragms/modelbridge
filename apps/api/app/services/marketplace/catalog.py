"""Marketplace discovery and search."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.extension import ExtensionPackage, ExtensionPublisher, PluginType, TrustLevel
from app.models.marketplace import (
    MARKETPLACE_CATEGORIES,
    MarketplaceAnalyticsEvent,
    MarketplaceItem,
    MarketplaceItemStatus,
    MarketplaceVisibility,
)

PLUGIN_TO_CONTENT = {
    PluginType.PROVIDER.value: "extension",
    PluginType.TOOL.value: "extension",
    PluginType.INTEGRATION.value: "integration",
    PluginType.AGENT_TEMPLATE.value: "agent",
    PluginType.WORKFLOW_TEMPLATE.value: "workflow",
}


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:120] or "item"


def visibility_scope(visibility: str, org_id: uuid.UUID | None) -> str:
    if visibility == MarketplaceVisibility.ORGANIZATION and org_id:
        return f"org:{org_id}"
    if visibility == MarketplaceVisibility.PRIVATE and org_id:
        return f"private:{org_id}"
    return "public"


class MarketplaceCatalogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _accessible_filter(self, org_id: uuid.UUID | None):
        return or_(
            and_(
                MarketplaceItem.visibility == MarketplaceVisibility.PUBLIC,
                MarketplaceItem.status == MarketplaceItemStatus.PUBLISHED,
            ),
            and_(
                MarketplaceItem.visibility == MarketplaceVisibility.ORGANIZATION,
                MarketplaceItem.organization_id == org_id,
            ),
            and_(
                MarketplaceItem.visibility == MarketplaceVisibility.PRIVATE,
                MarketplaceItem.organization_id == org_id,
            ),
        )

    async def search(
        self,
        *,
        org_id: uuid.UUID | None = None,
        query: str | None = None,
        content_type: str | None = None,
        category: str | None = None,
        publisher_slug: str | None = None,
        official_only: bool = False,
        verified_only: bool = False,
        featured_only: bool = False,
        limit: int = 50,
    ) -> list[MarketplaceItem]:
        q = select(MarketplaceItem).where(self._accessible_filter(org_id))
        if query:
            like = f"%{query}%"
            q = q.where(
                or_(
                    MarketplaceItem.name.ilike(like),
                    MarketplaceItem.description.ilike(like),
                    MarketplaceItem.slug.ilike(like),
                )
            )
        if content_type:
            q = q.where(MarketplaceItem.content_type == content_type)
        if category:
            q = q.where(MarketplaceItem.category == category)
        if featured_only:
            q = q.where(MarketplaceItem.featured.is_(True))
        if publisher_slug:
            q = q.join(ExtensionPublisher, ExtensionPublisher.id == MarketplaceItem.publisher_id).where(
                ExtensionPublisher.slug == publisher_slug
            )
        if official_only or verified_only:
            q = q.join(ExtensionPackage, ExtensionPackage.id == MarketplaceItem.package_id)
            if official_only:
                q = q.where(ExtensionPackage.trust_level == TrustLevel.OFFICIAL)
            if verified_only:
                q = q.join(ExtensionPublisher, ExtensionPublisher.id == MarketplaceItem.publisher_id).where(
                    ExtensionPublisher.verification_status.in_(["verified", "official"])
                )

        q = q.order_by(MarketplaceItem.featured.desc(), MarketplaceItem.updated_at.desc()).limit(min(limit, 100))
        result = await self.db.execute(q)
        return list(result.scalars().unique().all())

    async def get_by_slug(self, slug: str, *, org_id: uuid.UUID | None = None) -> MarketplaceItem | None:
        result = await self.db.execute(
            select(MarketplaceItem).where(
                MarketplaceItem.slug == slug,
                self._accessible_filter(org_id),
            )
        )
        item = result.scalar_one_or_none()
        if item:
            await self.record_view(item.id, org_id)
        return item

    async def get(self, item_id: uuid.UUID, *, org_id: uuid.UUID | None = None) -> MarketplaceItem | None:
        item = await self.db.get(MarketplaceItem, item_id)
        if not item:
            return None
        if item.visibility == MarketplaceVisibility.PUBLIC and item.status == MarketplaceItemStatus.PUBLISHED:
            return item
        if org_id and item.organization_id == org_id:
            return item
        return None

    async def record_view(self, item_id: uuid.UUID, org_id: uuid.UUID | None) -> None:
        item = await self.db.get(MarketplaceItem, item_id)
        if not item:
            return
        item.view_count += 1
        self.db.add(
            MarketplaceAnalyticsEvent(
                item_id=item_id,
                event_type="view",
                organization_id=org_id,
            )
        )
        await self.db.flush()

    async def discovery(self, *, org_id: uuid.UUID | None = None) -> dict:
        featured = await self.search(org_id=org_id, featured_only=True, limit=6)
        official = await self.search(org_id=org_id, official_only=True, limit=6)
        recent = await self.search(org_id=org_id, limit=6)
        popular = sorted(
            await self.search(org_id=org_id, limit=20),
            key=lambda i: i.install_count,
            reverse=True,
        )[:6]
        return {
            "featured": featured,
            "official": official,
            "recent": recent,
            "popular": popular,
            "categories": sorted(MARKETPLACE_CATEGORIES),
        }

    @staticmethod
    def content_type_from_plugin(plugin_type: str) -> str:
        return PLUGIN_TO_CONTENT.get(plugin_type, "template")
