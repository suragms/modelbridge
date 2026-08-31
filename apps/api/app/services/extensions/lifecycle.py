"""Extension installation lifecycle management."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.encryption import decrypt_secret, encrypt_secret
from app.models.extension import (
    ExtensionConfiguration,
    ExtensionInstallation,
    ExtensionPackage,
    ExtensionPackageVersion,
    InstallationStatus,
)
from app.services.audit import AuditService
from app.services.extensions.manifest import is_compatible, validate_manifest
from app.services.metrics import record_extension_event

MODELBRIDGE_VERSION = "1.0.0"

AUDIT_EXTENSION_INSTALLED = "extension.installed"
AUDIT_EXTENSION_ENABLED = "extension.enabled"
AUDIT_EXTENSION_DISABLED = "extension.disabled"
AUDIT_EXTENSION_UNINSTALLED = "extension.uninstalled"
AUDIT_EXTENSION_UPDATED = "extension.updated"
AUDIT_EXTENSION_CONFIG_CHANGED = "extension.config_changed"


class ExtensionLifecycleError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


class ExtensionLifecycleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = AuditService(db)

    async def _get_version(self, version_id: uuid.UUID) -> tuple[ExtensionPackageVersion, ExtensionPackage]:
        result = await self.db.execute(
            select(ExtensionPackageVersion, ExtensionPackage)
            .join(ExtensionPackage, ExtensionPackage.id == ExtensionPackageVersion.package_id)
            .where(ExtensionPackageVersion.id == version_id)
        )
        row = result.one_or_none()
        if not row:
            raise ExtensionLifecycleError("NOT_FOUND", "Package version not found")
        return row[0], row[1]

    async def validate_install(
        self,
        version_id: uuid.UUID,
        *,
        approved_permissions: list[str] | None = None,
    ) -> ExtensionPackageVersion:
        version, package = await self._get_version(version_id)
        manifest = version.manifest or {}
        validation = validate_manifest(manifest)
        if not validation.valid:
            raise ExtensionLifecycleError("INVALID_MANIFEST", "; ".join(validation.errors))

        min_ver = manifest.get("minimum_modelbridge_version", version.compatibility_version)
        if not is_compatible(str(min_ver), MODELBRIDGE_VERSION):
            raise ExtensionLifecycleError(
                "INCOMPATIBLE",
                f"Requires ModelBridge {min_ver}, running {MODELBRIDGE_VERSION}",
            )

        required_perms = version.permissions or manifest.get("permissions") or []
        if approved_permissions is not None:
            missing = set(required_perms) - set(approved_permissions)
            if missing:
                raise ExtensionLifecycleError(
                    "PERMISSION_DENIED",
                    f"Missing approved permissions: {sorted(missing)}",
                )
        return version

    async def install(
        self,
        org_id: uuid.UUID,
        version_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None,
        approved_permissions: list[str],
        config: dict | None = None,
        secrets: dict | None = None,
    ) -> ExtensionInstallation:
        version, package = await self._get_version(version_id)
        manifest = version.manifest or {}
        validation = validate_manifest(manifest)
        if not validation.valid:
            raise ExtensionLifecycleError("INVALID_MANIFEST", "; ".join(validation.errors))

        min_ver = manifest.get("minimum_modelbridge_version", version.compatibility_version)
        if not is_compatible(str(min_ver), MODELBRIDGE_VERSION):
            raise ExtensionLifecycleError(
                "INCOMPATIBLE",
                f"Requires ModelBridge {min_ver}, running {MODELBRIDGE_VERSION}",
            )

        required_perms = version.permissions or manifest.get("permissions") or []
        missing = set(required_perms) - set(approved_permissions)
        if missing:
            raise ExtensionLifecycleError(
                "PERMISSION_DENIED",
                f"Missing approved permissions: {sorted(missing)}",
            )

        existing = await self.db.execute(
            select(ExtensionInstallation).where(
                ExtensionInstallation.organization_id == org_id,
                ExtensionInstallation.package_version_id == version_id,
                ExtensionInstallation.status != InstallationStatus.UNINSTALLED,
            )
        )
        if existing.scalar_one_or_none():
            raise ExtensionLifecycleError("ALREADY_INSTALLED", "Package version already installed")

        installation = ExtensionInstallation(
            organization_id=org_id,
            package_version_id=version_id,
            status=InstallationStatus.INSTALLED,
            installed_by=user_id,
            health_status="healthy",
        )
        self.db.add(installation)
        await self.db.flush()

        enc_secrets = None
        if secrets:
            enc_secrets = encrypt_secret(json.dumps(secrets))

        self.db.add(
            ExtensionConfiguration(
                installation_id=installation.id,
                config=config or {},
                encrypted_secrets=enc_secrets,
            )
        )
        await self.audit.log(
            AUDIT_EXTENSION_INSTALLED,
            "extension_installation",
            resource_id=str(installation.id),
            metadata={"package_version_id": str(version_id), "permissions": approved_permissions},
            organization_id=org_id,
        )
        record_extension_event(event="installed", plugin_type=package.plugin_type)
        await self.db.flush()
        return installation

    async def enable(
        self,
        installation: ExtensionInstallation,
        *,
        user_id: uuid.UUID | None,
    ) -> ExtensionInstallation:
        if installation.status == InstallationStatus.ENABLED:
            return installation
        if installation.status not in {InstallationStatus.INSTALLED, InstallationStatus.DISABLED, InstallationStatus.ERROR}:
            raise ExtensionLifecycleError("INVALID_STATE", f"Cannot enable from {installation.status}")

        installation.status = InstallationStatus.ENABLED
        installation.enabled_by = user_id
        installation.enabled_at = datetime.now(UTC)
        installation.health_status = "healthy"
        installation.last_error = None

        await self.audit.log(
            AUDIT_EXTENSION_ENABLED,
            "extension_installation",
            resource_id=str(installation.id),
            organization_id=installation.organization_id,
        )
        pv = installation.package_version
        plugin_type = "unknown"
        if pv:
            pkg_result = await self.db.execute(
                select(ExtensionPackage).where(ExtensionPackage.id == pv.package_id)
            )
            pkg = pkg_result.scalar_one_or_none()
            if pkg:
                plugin_type = pkg.plugin_type
        record_extension_event(event="enabled", plugin_type=plugin_type)
        await self.db.flush()
        return installation

    async def disable(
        self,
        installation: ExtensionInstallation,
        *,
        reason: str | None = None,
    ) -> ExtensionInstallation:
        if installation.status != InstallationStatus.ENABLED:
            raise ExtensionLifecycleError("INVALID_STATE", "Extension is not enabled")
        installation.status = InstallationStatus.DISABLED
        installation.last_error = reason
        await self.audit.log(
            AUDIT_EXTENSION_DISABLED,
            "extension_installation",
            resource_id=str(installation.id),
            metadata={"reason": reason},
            organization_id=installation.organization_id,
        )
        record_extension_event(event="disabled", plugin_type="unknown")
        await self.db.flush()
        return installation

    async def uninstall(self, installation: ExtensionInstallation) -> ExtensionInstallation:
        installation.status = InstallationStatus.UNINSTALLED
        installation.health_status = "unknown"
        await self.audit.log(
            AUDIT_EXTENSION_UNINSTALLED,
            "extension_installation",
            resource_id=str(installation.id),
            organization_id=installation.organization_id,
        )
        record_extension_event(event="uninstalled", plugin_type="unknown")
        await self.db.flush()
        return installation

    async def record_execution(
        self,
        installation: ExtensionInstallation,
        *,
        success: bool,
        latency_ms: float | None = None,
        error: str | None = None,
    ) -> None:
        installation.execution_count += 1
        if success:
            installation.last_success_at = datetime.now(UTC)
            installation.health_status = "healthy"
            if latency_ms is not None:
                prev = installation.avg_latency_ms or latency_ms
                installation.avg_latency_ms = (prev + latency_ms) / 2
            record_extension_event(event="success", plugin_type="unknown")
        else:
            installation.failure_count += 1
            installation.last_error = error
            installation.health_status = "degraded" if installation.failure_count < 5 else "unhealthy"
            if installation.failure_count >= 5:
                installation.status = InstallationStatus.ERROR
            record_extension_event(event="failure", plugin_type="unknown")

    async def update_config(
        self,
        installation: ExtensionInstallation,
        config: dict,
        secrets: dict | None = None,
    ) -> ExtensionConfiguration:
        cfg = installation.configuration
        if not cfg:
            cfg = ExtensionConfiguration(installation_id=installation.id, config=config)
            self.db.add(cfg)
        else:
            cfg.config = config
            cfg.updated_at = datetime.now(UTC)
        if secrets is not None:
            cfg.encrypted_secrets = encrypt_secret(json.dumps(secrets)) if secrets else None
        await self.audit.log(
            AUDIT_EXTENSION_CONFIG_CHANGED,
            "extension_installation",
            resource_id=str(installation.id),
            organization_id=installation.organization_id,
        )
        await self.db.flush()
        return cfg

    @staticmethod
    def safe_config_response(cfg: ExtensionConfiguration | None) -> dict:
        if not cfg:
            return {"config": {}, "has_secrets": False}
        return {"config": cfg.config or {}, "has_secrets": bool(cfg.encrypted_secrets)}
