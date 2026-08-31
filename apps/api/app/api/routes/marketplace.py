"""Marketplace and community ecosystem APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.org_context import OrgContext
from app.auth.rbac import Permission, require_permission
from app.db.base import get_db
from app.models.extension import ExtensionPackage, ExtensionPackageVersion, ExtensionPublisher
from app.models.marketplace import (
    MarketplaceItem,
    MarketplaceReport,
    MarketplaceReview,
    MarketplaceSubmission,
    ReportStatus,
)
from app.schemas.marketplace import (
    MarketplaceDiscoveryResponse,
    MarketplaceInstallHistoryResponse,
    MarketplaceInstallRequest,
    MarketplaceItemCreate,
    MarketplaceItemResponse,
    MarketplaceReportCreate,
    MarketplaceReviewCreate,
    MarketplaceSubmissionResponse,
    MarketplaceVersionCreate,
    MarketplaceVersionResponse,
    PublisherCreate,
    PublisherResponse,
)
from app.services.audit import AuditService
from app.services.marketplace.catalog import MarketplaceCatalogService
from app.services.marketplace.installation import MarketplaceInstallService
from app.services.marketplace.publishing import MarketplacePublishingService

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])
publishers_router = APIRouter(prefix="/publishers", tags=["Publishers"])
admin_router = APIRouter(prefix="/admin/marketplace", tags=["Marketplace Admin"])


async def _item_response(db: AsyncSession, item: MarketplaceItem) -> MarketplaceItemResponse:
    pkg = await db.get(ExtensionPackage, item.package_id)
    pub = await db.get(ExtensionPublisher, item.publisher_id) if item.publisher_id else None
    versions_result = await db.execute(
        select(ExtensionPackageVersion)
        .where(ExtensionPackageVersion.package_id == item.package_id)
        .order_by(ExtensionPackageVersion.published_at.desc())
    )
    versions = list(versions_result.scalars().all())
    current = next((v for v in versions if v.id == item.current_version_id), versions[0] if versions else None)

    def ver_resp(v: ExtensionPackageVersion) -> MarketplaceVersionResponse:
        return MarketplaceVersionResponse(
            id=v.id,
            version=v.version,
            compatibility_version=v.compatibility_version,
            permissions=list(v.permissions or []),
            changelog=v.changelog,
            published_at=v.published_at,
        )

    return MarketplaceItemResponse(
        id=item.id,
        slug=item.slug,
        name=item.name,
        description=item.description,
        content_type=item.content_type,
        category=item.category,
        status=item.status,
        visibility=item.visibility,
        featured=item.featured,
        install_count=item.install_count,
        view_count=item.view_count,
        security_review_status=item.security_review_status,
        publisher_slug=pub.slug if pub else None,
        publisher_name=pub.name if pub else None,
        publisher_verification=getattr(pub, "verification_status", None) if pub else None,
        trust_level=pkg.trust_level if pkg else None,
        documentation_url=item.documentation_url,
        current_version=ver_resp(current) if current else None,
        versions=[ver_resp(v) for v in versions],
        created_at=item.created_at,
        updated_at=item.updated_at,
        published_at=item.published_at,
    )


@router.get("/discovery", response_model=MarketplaceDiscoveryResponse)
async def marketplace_discovery(
    ctx: OrgContext = Depends(require_permission(Permission.MARKETPLACE_READ)),
    db: AsyncSession = Depends(get_db),
):
    data = await MarketplaceCatalogService(db).discovery(org_id=ctx.organization_id)
    return MarketplaceDiscoveryResponse(
        featured=[await _item_response(db, i) for i in data["featured"]],
        official=[await _item_response(db, i) for i in data["official"]],
        recent=[await _item_response(db, i) for i in data["recent"]],
        popular=[await _item_response(db, i) for i in data["popular"]],
        categories=data["categories"],
    )


@router.get("/categories")
async def list_categories(
    ctx: OrgContext = Depends(require_permission(Permission.MARKETPLACE_READ)),
):
    from app.models.marketplace import MARKETPLACE_CATEGORIES

    return {"categories": sorted(MARKETPLACE_CATEGORIES)}


@router.get("/items", response_model=list[MarketplaceItemResponse])
async def search_items(
    q: str | None = None,
    content_type: str | None = None,
    category: str | None = None,
    publisher: str | None = None,
    official: bool = False,
    verified: bool = False,
    featured: bool = False,
    limit: int = 50,
    ctx: OrgContext = Depends(require_permission(Permission.MARKETPLACE_READ)),
    db: AsyncSession = Depends(get_db),
):
    items = await MarketplaceCatalogService(db).search(
        org_id=ctx.organization_id,
        query=q,
        content_type=content_type,
        category=category,
        publisher_slug=publisher,
        official_only=official,
        verified_only=verified,
        featured_only=featured,
        limit=limit,
    )
    return [await _item_response(db, i) for i in items]


@router.get("/items/{slug}", response_model=MarketplaceItemResponse)
async def get_item(
    slug: str,
    ctx: OrgContext = Depends(require_permission(Permission.MARKETPLACE_READ)),
    db: AsyncSession = Depends(get_db),
):
    item = await MarketplaceCatalogService(db).get_by_slug(slug, org_id=ctx.organization_id)
    if not item:
        raise HTTPException(status_code=404, detail="Marketplace item not found")
    await db.commit()
    return await _item_response(db, item)


@router.post("/items", response_model=MarketplaceItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: MarketplaceItemCreate,
    ctx: OrgContext = Depends(require_permission(Permission.MARKETPLACE_PUBLISH)),
    db: AsyncSession = Depends(get_db),
):
    svc = MarketplacePublishingService(db)
    try:
        item, _version = await svc.create_item_from_manifest(
            payload.manifest,
            org_id=ctx.organization_id,
            publisher_slug=payload.publisher_slug,
            publisher_name=payload.publisher_name,
            visibility=payload.visibility,
            user_id=ctx.user.id,
        )
        await db.commit()
        return await _item_response(db, item)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/items/{item_id}/submit", response_model=MarketplaceSubmissionResponse)
async def submit_item(
    item_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.MARKETPLACE_PUBLISH)),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(MarketplaceItem, item_id)
    if not item or (item.organization_id and item.organization_id != ctx.organization_id):
        raise HTTPException(status_code=404, detail="Item not found")
    try:
        submission = await MarketplacePublishingService(db).submit(item, user_id=ctx.user.id)
        await db.commit()
        return MarketplaceSubmissionResponse.model_validate(submission)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/items/{item_id}/versions", response_model=MarketplaceVersionResponse)
async def add_version(
    item_id: uuid.UUID,
    payload: MarketplaceVersionCreate,
    ctx: OrgContext = Depends(require_permission(Permission.MARKETPLACE_PUBLISH)),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(MarketplaceItem, item_id)
    if not item or (item.organization_id and item.organization_id != ctx.organization_id):
        raise HTTPException(status_code=404, detail="Item not found")
    try:
        version = await MarketplacePublishingService(db).add_version(
            item, payload.manifest, user_id=ctx.user.id
        )
        await db.commit()
        return MarketplaceVersionResponse(
            id=version.id,
            version=version.version,
            compatibility_version=version.compatibility_version,
            permissions=list(version.permissions or []),
            changelog=version.changelog,
            published_at=version.published_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/items/{item_id}/install")
async def install_item(
    item_id: uuid.UUID,
    payload: MarketplaceInstallRequest,
    ctx: OrgContext = Depends(require_permission(Permission.EXTENSIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    item = await MarketplaceCatalogService(db).get(item_id, org_id=ctx.organization_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    try:
        inst, history = await MarketplaceInstallService(db).install(
            item,
            org_id=ctx.organization_id,
            user_id=ctx.user.id,
            approved_permissions=payload.approved_permissions,
            version_id=payload.version_id,
            enable=payload.enable,
            config=payload.config,
        )
        await db.commit()
        return {
            "installation_id": str(inst.id),
            "history_id": str(history.id),
            "status": inst.status,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/install-history", response_model=list[MarketplaceInstallHistoryResponse])
async def install_history(
    item_id: uuid.UUID | None = None,
    ctx: OrgContext = Depends(require_permission(Permission.MARKETPLACE_READ)),
    db: AsyncSession = Depends(get_db),
):
    rows = await MarketplaceInstallService(db).install_history(ctx.organization_id, item_id=item_id)
    return [MarketplaceInstallHistoryResponse.model_validate(r) for r in rows]


@router.post("/items/{item_id}/reviews", status_code=status.HTTP_201_CREATED)
async def create_review(
    item_id: uuid.UUID,
    payload: MarketplaceReviewCreate,
    ctx: OrgContext = Depends(require_permission(Permission.MARKETPLACE_READ)),
    db: AsyncSession = Depends(get_db),
):
    item = await MarketplaceCatalogService(db).get(item_id, org_id=ctx.organization_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    review = MarketplaceReview(
        item_id=item_id,
        organization_id=ctx.organization_id,
        reviewer_id=ctx.user.id,
        rating=payload.rating,
        title=payload.title,
        body=payload.body,
    )
    db.add(review)
    await db.commit()
    return {"id": str(review.id), "rating": review.rating}


@router.post("/items/{item_id}/report", status_code=status.HTTP_201_CREATED)
async def report_item(
    item_id: uuid.UUID,
    payload: MarketplaceReportCreate,
    ctx: OrgContext = Depends(require_permission(Permission.MARKETPLACE_READ)),
    db: AsyncSession = Depends(get_db),
):
    item = await MarketplaceCatalogService(db).get(item_id, org_id=ctx.organization_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    report = MarketplaceReport(
        item_id=item_id,
        reporter_id=ctx.user.id,
        organization_id=ctx.organization_id,
        reason=payload.reason,
        details=payload.details,
    )
    db.add(report)
    await db.commit()
    return {"id": str(report.id), "status": report.status}


@publishers_router.get("/{slug}", response_model=PublisherResponse)
async def get_publisher(
    slug: str,
    ctx: OrgContext = Depends(require_permission(Permission.MARKETPLACE_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ExtensionPublisher).where(ExtensionPublisher.slug == slug))
    pub = result.scalar_one_or_none()
    if not pub:
        raise HTTPException(status_code=404, detail="Publisher not found")
    return PublisherResponse(
        id=pub.id,
        name=pub.name,
        slug=pub.slug,
        description=getattr(pub, "description", None),
        website=getattr(pub, "website", None) or pub.homepage,
        verification_status=getattr(pub, "verification_status", "unverified"),
        is_verified=pub.is_verified,
        created_at=pub.created_at,
    )


@publishers_router.post("/", response_model=PublisherResponse, status_code=status.HTTP_201_CREATED)
async def create_publisher(
    payload: PublisherCreate,
    ctx: OrgContext = Depends(require_permission(Permission.MARKETPLACE_PUBLISH)),
    db: AsyncSession = Depends(get_db),
):
    pub = await MarketplacePublishingService(db).get_or_create_publisher(
        org_id=ctx.organization_id,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        website=payload.website,
    )
    await db.commit()
    return PublisherResponse(
        id=pub.id,
        name=pub.name,
        slug=pub.slug,
        description=pub.description,
        website=pub.website or pub.homepage,
        verification_status=pub.verification_status,
        is_verified=pub.is_verified,
        created_at=pub.created_at,
    )


@publishers_router.get("/{slug}/items", response_model=list[MarketplaceItemResponse])
async def publisher_items(
    slug: str,
    ctx: OrgContext = Depends(require_permission(Permission.MARKETPLACE_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ExtensionPublisher).where(ExtensionPublisher.slug == slug))
    pub = result.scalar_one_or_none()
    if not pub:
        raise HTTPException(status_code=404, detail="Publisher not found")
    items = await MarketplacePublishingService(db).list_publisher_items(pub.id)
    visible = []
    for item in items:
        if await MarketplaceCatalogService(db).get(item.id, org_id=ctx.organization_id):
            visible.append(item)
    return [await _item_response(db, i) for i in visible]


@admin_router.get("/submissions", response_model=list[MarketplaceSubmissionResponse])
async def admin_list_submissions(
    ctx: OrgContext = Depends(require_permission(Permission.MARKETPLACE_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MarketplaceSubmission).order_by(MarketplaceSubmission.created_at.desc()).limit(100)
    )
    return [MarketplaceSubmissionResponse.model_validate(s) for s in result.scalars().all()]


@admin_router.post("/items/{item_id}/publish", response_model=MarketplaceItemResponse)
async def admin_publish(
    item_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.MARKETPLACE_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(MarketplaceItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item = await MarketplacePublishingService(db).publish(item, reviewer_id=ctx.user.id)
    audit = AuditService(db)
    await audit.log(
        "marketplace.published", "marketplace_item", str(item.id),
        actor=ctx.user, organization_id=ctx.organization_id,
    )
    await db.commit()
    return await _item_response(db, item)


@admin_router.post("/items/{item_id}/reject", response_model=MarketplaceItemResponse)
async def admin_reject(
    item_id: uuid.UUID,
    notes: str = Query(..., min_length=3),
    ctx: OrgContext = Depends(require_permission(Permission.MARKETPLACE_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(MarketplaceItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item = await MarketplacePublishingService(db).reject(item, reviewer_id=ctx.user.id, notes=notes)
    audit = AuditService(db)
    await audit.log(
        "marketplace.rejected", "marketplace_item", str(item.id),
        actor=ctx.user, organization_id=ctx.organization_id, metadata={"notes": notes},
    )
    await db.commit()
    return await _item_response(db, item)


@admin_router.get("/reports")
async def admin_reports(
    ctx: OrgContext = Depends(require_permission(Permission.MARKETPLACE_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MarketplaceReport)
        .where(MarketplaceReport.status == ReportStatus.OPEN)
        .order_by(MarketplaceReport.created_at.desc())
        .limit(100)
    )
    return [
        {
            "id": str(r.id),
            "item_id": str(r.item_id),
            "reason": r.reason,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
        }
        for r in result.scalars().all()
    ]
