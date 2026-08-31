"""Seed marketplace listings from official extension packages."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.extension import ExtensionPackage, ExtensionRegistry, TrustLevel
from app.models.marketplace import MarketplaceItem, MarketplaceItemStatus, MarketplaceVisibility
from app.services.marketplace.catalog import MarketplaceCatalogService, slugify, visibility_scope


async def seed_marketplace_items(db: AsyncSession) -> None:
    """Create marketplace listings for official published packages (idempotent)."""
    result = await db.execute(
        select(ExtensionPackage)
        .join(ExtensionRegistry, ExtensionRegistry.id == ExtensionPackage.registry_id)
        .where(
            ExtensionRegistry.organization_id.is_(None),
            ExtensionPackage.trust_level == TrustLevel.OFFICIAL,
        )
    )
    catalog = MarketplaceCatalogService(db)
    for pkg in result.scalars().all():
        existing = await db.execute(
            select(MarketplaceItem).where(MarketplaceItem.package_id == pkg.id)
        )
        if existing.scalar_one_or_none():
            continue
        latest = pkg.versions[0] if pkg.versions else None
        item = MarketplaceItem(
            package_id=pkg.id,
            publisher_id=pkg.publisher_id,
            organization_id=None,
            content_type=catalog.content_type_from_plugin(pkg.plugin_type),
            name=pkg.display_name,
            slug=slugify(pkg.name),
            description=pkg.description,
            category=pkg.category,
            status=MarketplaceItemStatus.PUBLISHED,
            visibility=MarketplaceVisibility.PUBLIC,
            visibility_scope=visibility_scope(MarketplaceVisibility.PUBLIC, None),
            featured=True,
            current_version_id=latest.id if latest else None,
            security_review_status="approved",
        )
        db.add(item)
    await db.flush()
