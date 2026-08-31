"""Extension marketplace and installation APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.org_context import OrgContext
from app.auth.rbac import Permission, require_permission
from app.db.base import get_db
from app.models.extension import (
    ExtensionInstallation,
    ExtensionPackage,
    ExtensionPackageVersion,
    ExtensionRegistry,
    InstallationStatus,
    PluginType,
)
from app.schemas.extensions import (
    InstallRequest,
    InstallationResponse,
    PackageResponse,
    PackageVersionResponse,
    PublishRequest,
    RegistryCreateRequest,
    UpdateConfigRequest,
)
from app.services.extensions.lifecycle import ExtensionLifecycleError, ExtensionLifecycleService
from app.services.extensions.registry import ExtensionRegistryService, seed_official_packages

router = APIRouter(prefix="/extensions", tags=["Extensions"])


def _installation_response(inst: ExtensionInstallation) -> InstallationResponse:
    pv = inst.package_version
    pkg = pv.package if pv else None
    pub = pkg.publisher if pkg else None
    return InstallationResponse(
        id=inst.id,
        organization_id=inst.organization_id,
        status=inst.status,
        health_status=inst.health_status,
        last_error=inst.last_error,
        failure_count=inst.failure_count,
        execution_count=inst.execution_count,
        avg_latency_ms=inst.avg_latency_ms,
        installed_at=inst.installed_at,
        enabled_at=inst.enabled_at,
        package_name=pkg.name if pkg else None,
        package_display_name=pkg.display_name if pkg else None,
        plugin_type=pkg.plugin_type if pkg else None,
        version=pv.version if pv else None,
        permissions=list(pv.permissions or []) if pv else [],
        trust_level=pkg.trust_level if pkg else None,
    )


def _package_response(pkg: ExtensionPackage) -> PackageResponse:
    return PackageResponse(
        id=pkg.id,
        name=pkg.name,
        display_name=pkg.display_name,
        description=pkg.description,
        plugin_type=pkg.plugin_type,
        trust_level=pkg.trust_level,
        category=pkg.category,
        publisher_name=pkg.publisher.name if pkg.publisher else None,
        versions=[
            PackageVersionResponse(
                id=v.id,
                version=v.version,
                compatibility_version=v.compatibility_version,
                permissions=list(v.permissions or []),
                configuration_schema=v.configuration_schema,
                published_at=v.published_at,
            )
            for v in (pkg.versions or [])
        ],
    )


async def _get_installation(
    db: AsyncSession, org_id: uuid.UUID, installation_id: uuid.UUID
) -> ExtensionInstallation:
    result = await db.execute(
        select(ExtensionInstallation)
        .options(
            selectinload(ExtensionInstallation.package_version).selectinload(ExtensionPackageVersion.package),
            selectinload(ExtensionInstallation.configuration),
        )
        .where(
            ExtensionInstallation.id == installation_id,
            ExtensionInstallation.organization_id == org_id,
            ExtensionInstallation.status != InstallationStatus.UNINSTALLED,
        )
    )
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404, detail="Installation not found")
    return inst



@router.get("/packages", response_model=list[PackageResponse])
async def search_packages(
    ctx: OrgContext = Depends(require_permission(Permission.EXTENSIONS_READ)),
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(None),
    plugin_type: str | None = Query(None),
    trust_level: str | None = Query(None),
    category: str | None = Query(None),
):
    svc = ExtensionRegistryService(db)
    packages = await svc.search_packages(
        org_id=ctx.organization_id,
        query=q,
        plugin_type=plugin_type,
        trust_level=trust_level,
        category=category,
    )
    return [_package_response(p) for p in packages]


@router.get("/packages/{package_id}", response_model=PackageResponse)
async def get_package(
    package_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.EXTENSIONS_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ExtensionPackage)
        .options(selectinload(ExtensionPackage.versions), selectinload(ExtensionPackage.publisher))
        .where(ExtensionPackage.id == package_id)
    )
    pkg = result.scalar_one_or_none()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    return _package_response(pkg)


@router.post("/publish", response_model=PackageVersionResponse, status_code=201)
async def publish_package(
    payload: PublishRequest,
    ctx: OrgContext = Depends(require_permission(Permission.EXTENSIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    svc = ExtensionRegistryService(db)
    try:
        version = await svc.publish_package(
            payload.manifest,
            registry_id=None,
            org_id=ctx.organization_id,
            publisher_slug=payload.publisher_slug,
            publisher_name=payload.publisher_name,
            trust_level=payload.trust_level,
            category=payload.category,
            user_id=ctx.user.id,
        )
        await db.commit()
        return PackageVersionResponse.model_validate(version)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/installations", response_model=list[InstallationResponse])
async def list_installations(
    ctx: OrgContext = Depends(require_permission(Permission.EXTENSIONS_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ExtensionInstallation)
        .options(selectinload(ExtensionInstallation.package_version).selectinload(ExtensionPackageVersion.package))
        .where(
            ExtensionInstallation.organization_id == ctx.organization_id,
            ExtensionInstallation.status != InstallationStatus.UNINSTALLED,
        )
        .order_by(ExtensionInstallation.installed_at.desc())
    )
    return [_installation_response(i) for i in result.scalars().all()]


@router.get("/installations/{installation_id}", response_model=InstallationResponse)
async def get_installation(
    installation_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.EXTENSIONS_READ)),
    db: AsyncSession = Depends(get_db),
):
    inst = await _get_installation(db, ctx.organization_id, installation_id)
    return _installation_response(inst)


@router.get("/installations/{installation_id}/config")
async def get_installation_config(
    installation_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.EXTENSIONS_READ)),
    db: AsyncSession = Depends(get_db),
):
    inst = await _get_installation(db, ctx.organization_id, installation_id)
    lifecycle = ExtensionLifecycleService(db)
    return lifecycle.safe_config_response(inst.configuration)


@router.post("/installations", response_model=InstallationResponse, status_code=201)
async def install_extension(
    payload: InstallRequest,
    ctx: OrgContext = Depends(require_permission(Permission.EXTENSIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    lifecycle = ExtensionLifecycleService(db)
    try:
        inst = await lifecycle.install(
            ctx.organization_id,
            payload.package_version_id,
            user_id=ctx.user.id,
            approved_permissions=payload.approved_permissions,
            config=payload.config,
            secrets=payload.secrets,
        )
        if payload.enable:
            inst = await lifecycle.enable(inst, user_id=ctx.user.id)
        await db.commit()
        await db.refresh(inst)
        inst = await _get_installation(db, ctx.organization_id, inst.id)
        return _installation_response(inst)
    except ExtensionLifecycleError as e:
        raise HTTPException(status_code=400, detail={"code": e.code, "message": str(e)}) from e


@router.post("/installations/{installation_id}/enable", response_model=InstallationResponse)
async def enable_extension(
    installation_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.EXTENSIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    inst = await _get_installation(db, ctx.organization_id, installation_id)
    lifecycle = ExtensionLifecycleService(db)
    try:
        inst = await lifecycle.enable(inst, user_id=ctx.user.id)
        await db.commit()
        return _installation_response(inst)
    except ExtensionLifecycleError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/installations/{installation_id}/disable", response_model=InstallationResponse)
async def disable_extension(
    installation_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.EXTENSIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    inst = await _get_installation(db, ctx.organization_id, installation_id)
    lifecycle = ExtensionLifecycleService(db)
    try:
        inst = await lifecycle.disable(inst)
        await db.commit()
        return _installation_response(inst)
    except ExtensionLifecycleError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/installations/{installation_id}", response_model=InstallationResponse)
async def uninstall_extension(
    installation_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.EXTENSIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    inst = await _get_installation(db, ctx.organization_id, installation_id)
    lifecycle = ExtensionLifecycleService(db)
    inst = await lifecycle.uninstall(inst)
    await db.commit()
    return _installation_response(inst)


@router.patch("/installations/{installation_id}/config")
async def update_installation_config(
    installation_id: uuid.UUID,
    payload: UpdateConfigRequest,
    ctx: OrgContext = Depends(require_permission(Permission.EXTENSIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    inst = await _get_installation(db, ctx.organization_id, installation_id)
    lifecycle = ExtensionLifecycleService(db)
    cfg = await lifecycle.update_config(inst, payload.config, payload.secrets)
    await db.commit()
    return lifecycle.safe_config_response(cfg)


@router.post("/registries", status_code=201)
async def create_registry(
    payload: RegistryCreateRequest,
    ctx: OrgContext = Depends(require_permission(Permission.EXTENSIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    from app.auth.encryption import encrypt_secret

    reg = ExtensionRegistry(
        organization_id=ctx.organization_id,
        name=payload.name,
        registry_type=payload.registry_type,
        base_url=payload.base_url,
        encrypted_auth=encrypt_secret(payload.auth_token) if payload.auth_token else None,
    )
    db.add(reg)
    await db.commit()
    return {"id": str(reg.id), "name": reg.name}


@router.post("/seed-official")
async def seed_official(
    ctx: OrgContext = Depends(require_permission(Permission.EXTENSIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Seed official packages (admin only, idempotent)."""
    del ctx
    await seed_official_packages(db)
    await db.commit()
    return {"status": "ok"}
