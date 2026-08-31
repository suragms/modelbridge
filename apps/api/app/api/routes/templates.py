"""Template gallery and installation APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.org_context import OrgContext
from app.auth.rbac import Permission, require_permission
from app.db.base import get_db
from app.models.extension import ExtensionInstallation, ExtensionPackage, ExtensionPackageVersion, InstallationStatus, PluginType
from app.schemas.extensions import PackageResponse, PackageVersionResponse, TemplateInstallRequest
from app.services.extensions.registry import ExtensionRegistryService
from app.services.extensions.templates import TemplateInstallError, install_template_from_installation

router = APIRouter(prefix="/templates", tags=["Templates"])

_TEMPLATE_TYPES = {PluginType.AGENT_TEMPLATE.value, PluginType.WORKFLOW_TEMPLATE.value}


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


@router.get("", response_model=list[PackageResponse])
async def list_templates(
    ctx: OrgContext = Depends(require_permission(Permission.EXTENSIONS_READ)),
    db: AsyncSession = Depends(get_db),
    plugin_type: str | None = Query(None),
    trust_level: str | None = Query(None),
):
    svc = ExtensionRegistryService(db)
    agent_type = plugin_type or None
    packages = await svc.search_packages(
        org_id=ctx.organization_id,
        plugin_type=agent_type,
        trust_level=trust_level,
    )
    templates = [p for p in packages if p.plugin_type in _TEMPLATE_TYPES]
    if not plugin_type:
        templates = [p for p in templates if p.plugin_type in _TEMPLATE_TYPES]
    elif plugin_type not in _TEMPLATE_TYPES:
        return []
    else:
        templates = [p for p in templates if p.plugin_type == plugin_type]
    return [_package_response(p) for p in templates]


@router.post("/installations/{installation_id}/apply")
async def apply_template(
    installation_id: uuid.UUID,
    payload: TemplateInstallRequest,
    ctx: OrgContext = Depends(require_permission(Permission.EXTENSIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ExtensionInstallation)
        .options(selectinload(ExtensionInstallation.package_version).selectinload(ExtensionPackageVersion.package))
        .where(
            ExtensionInstallation.id == installation_id,
            ExtensionInstallation.organization_id == ctx.organization_id,
            ExtensionInstallation.status != InstallationStatus.UNINSTALLED,
        )
    )
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404, detail="Installation not found")

    try:
        resource = await install_template_from_installation(
            db,
            inst,
            payload.parameters,
            user_id=ctx.user.id,
            activate=payload.activate,
        )
        await db.commit()
        return {
            "resource_type": inst.package_version.package.plugin_type,
            "resource_id": str(resource.id),
            "status": getattr(resource, "status", "created"),
        }
    except TemplateInstallError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
