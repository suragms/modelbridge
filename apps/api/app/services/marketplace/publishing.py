"""Marketplace publishing workflow."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.extension import ExtensionPackage, ExtensionPackageVersion, ExtensionPublisher, TrustLevel
from app.models.marketplace import (
    MarketplaceItem,
    MarketplaceItemStatus,
    MarketplaceSubmission,
    MarketplaceVisibility,
    SecurityReviewStatus,
    SubmissionStatus,
)
from app.services.extensions.registry import ExtensionRegistryService
from app.services.marketplace.catalog import MarketplaceCatalogService, slugify, visibility_scope
from app.services.marketplace.validation import run_validation_pipeline
from app.services.metrics import record_marketplace_publication, record_marketplace_validation_failure


class MarketplacePublishingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.registry = ExtensionRegistryService(db)
        self.catalog = MarketplaceCatalogService(db)

    async def create_item_from_manifest(
        self,
        manifest: dict,
        *,
        org_id: uuid.UUID | None,
        publisher_slug: str,
        publisher_name: str,
        visibility: str = MarketplaceVisibility.PUBLIC,
        user_id: uuid.UUID | None = None,
    ) -> tuple[MarketplaceItem, ExtensionPackageVersion]:
        validation = run_validation_pipeline(manifest)
        if not validation.valid:
            record_marketplace_validation_failure()
            raise ValueError("; ".join(validation.errors))

        trust = TrustLevel.COMMUNITY
        if org_id is None:
            trust = TrustLevel.OFFICIAL if manifest.get("author") == "ModelBridge" else TrustLevel.COMMUNITY

        version = await self.registry.publish_package(
            manifest,
            registry_id=None,
            org_id=org_id,
            publisher_slug=publisher_slug,
            publisher_name=publisher_name,
            trust_level=trust,
            category=manifest.get("category"),
            user_id=user_id,
        )
        pkg = await self.db.get(ExtensionPackage, version.package_id)
        if not pkg:
            raise ValueError("Package not found after publish")

        slug = slugify(manifest.get("name", pkg.name))
        scope = visibility_scope(visibility, org_id)
        item = MarketplaceItem(
            package_id=pkg.id,
            publisher_id=pkg.publisher_id,
            organization_id=org_id,
            content_type=self.catalog.content_type_from_plugin(pkg.plugin_type),
            name=pkg.display_name,
            slug=slug,
            description=pkg.description,
            category=pkg.category,
            status=MarketplaceItemStatus.DRAFT,
            visibility=visibility,
            visibility_scope=scope,
            current_version_id=version.id,
            security_review_status=validation.security_status,
            created_by=user_id,
        )
        self.db.add(item)
        await self.db.flush()
        return item, version

    async def submit(self, item: MarketplaceItem, *, user_id: uuid.UUID | None) -> MarketplaceSubmission:
        if item.status not in {MarketplaceItemStatus.DRAFT, MarketplaceItemStatus.REJECTED}:
            raise ValueError(f"Cannot submit item in status {item.status}")
        if not item.current_version_id:
            raise ValueError("No version to submit")

        version = await self.db.get(ExtensionPackageVersion, item.current_version_id)
        if not version:
            raise ValueError("Version not found")

        validation = run_validation_pipeline(version.manifest or {})
        submission = MarketplaceSubmission(
            item_id=item.id,
            version_id=version.id,
            status=SubmissionStatus.PENDING if validation.valid else SubmissionStatus.REJECTED,
            validation_errors=validation.errors,
            security_review_status=validation.security_status,
            submitted_by=user_id,
        )
        item.status = (
            MarketplaceItemStatus.SUBMITTED if validation.valid else MarketplaceItemStatus.REJECTED
        )
        item.security_review_status = validation.security_status
        if not validation.valid:
            record_marketplace_validation_failure()
        self.db.add(submission)
        await self.db.flush()
        return submission

    async def publish(
        self,
        item: MarketplaceItem,
        *,
        reviewer_id: uuid.UUID | None = None,
        notes: str | None = None,
    ) -> MarketplaceItem:
        if item.status not in {
            MarketplaceItemStatus.SUBMITTED,
            MarketplaceItemStatus.UNDER_REVIEW,
            MarketplaceItemStatus.DRAFT,
        }:
            raise ValueError(f"Cannot publish from status {item.status}")

        result = await self.db.execute(
            select(MarketplaceSubmission)
            .where(MarketplaceSubmission.item_id == item.id)
            .order_by(MarketplaceSubmission.created_at.desc())
            .limit(1)
        )
        submission = result.scalar_one_or_none()
        if submission and submission.validation_errors:
            raise ValueError("Submission has validation errors")

        item.status = MarketplaceItemStatus.PUBLISHED
        item.published_at = datetime.now(UTC)
        item.security_review_status = SecurityReviewStatus.APPROVED
        if submission:
            submission.status = SubmissionStatus.APPROVED
            submission.reviewed_by = reviewer_id
            submission.review_notes = notes
            submission.reviewed_at = datetime.now(UTC)

        record_marketplace_publication(content_type=item.content_type)
        await self.db.flush()
        return item

    async def reject(
        self,
        item: MarketplaceItem,
        *,
        reviewer_id: uuid.UUID | None,
        notes: str,
    ) -> MarketplaceItem:
        item.status = MarketplaceItemStatus.REJECTED
        result = await self.db.execute(
            select(MarketplaceSubmission)
            .where(MarketplaceSubmission.item_id == item.id)
            .order_by(MarketplaceSubmission.created_at.desc())
            .limit(1)
        )
        submission = result.scalar_one_or_none()
        if submission:
            submission.status = SubmissionStatus.REJECTED
            submission.reviewed_by = reviewer_id
            submission.review_notes = notes
            submission.reviewed_at = datetime.now(UTC)
        await self.db.flush()
        return item

    async def add_version(
        self,
        item: MarketplaceItem,
        manifest: dict,
        *,
        user_id: uuid.UUID | None,
    ) -> ExtensionPackageVersion:
        validation = run_validation_pipeline(manifest)
        if not validation.valid:
            record_marketplace_validation_failure()
            raise ValueError("; ".join(validation.errors))

        pkg = await self.db.get(ExtensionPackage, item.package_id)
        if not pkg:
            raise ValueError("Package not found")

        pub = await self.db.get(ExtensionPublisher, item.publisher_id) if item.publisher_id else None
        version = await self.registry.publish_package(
            manifest,
            registry_id=pkg.registry_id,
            org_id=item.organization_id,
            publisher_slug=pub.slug if pub else "community",
            publisher_name=pub.name if pub else "Community",
            trust_level=pkg.trust_level,
            category=pkg.category,
            user_id=user_id,
        )
        item.current_version_id = version.id
        item.status = MarketplaceItemStatus.DRAFT
        item.security_review_status = validation.security_status
        item.updated_at = datetime.now(UTC)
        await self.db.flush()
        return version

    async def list_publisher_items(self, publisher_id: uuid.UUID) -> list[MarketplaceItem]:
        result = await self.db.execute(
            select(MarketplaceItem)
            .where(MarketplaceItem.publisher_id == publisher_id)
            .order_by(MarketplaceItem.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_or_create_publisher(
        self,
        *,
        org_id: uuid.UUID | None,
        name: str,
        slug: str,
        description: str | None = None,
        website: str | None = None,
    ) -> ExtensionPublisher:
        result = await self.db.execute(select(ExtensionPublisher).where(ExtensionPublisher.slug == slug))
        pub = result.scalar_one_or_none()
        if pub:
            return pub
        pub = ExtensionPublisher(
            organization_id=org_id,
            name=name,
            slug=slug,
            description=description,
            website=website,
            verification_status="unverified",
        )
        self.db.add(pub)
        await self.db.flush()
        return pub
