"""Configuration versioning, comparison, promotion, and deployment."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enterprise import (
    ConfigurationDeployment,
    ConfigurationVersion,
    DeploymentStatus,
    Environment,
    EnvironmentKind,
)
from app.services.metrics import record_config_deployment

PROMOTION_CHAIN = {
    EnvironmentKind.DEVELOPMENT: EnvironmentKind.STAGING,
    EnvironmentKind.STAGING: EnvironmentKind.PRODUCTION,
}


def safe_diff(a: dict, b: dict) -> dict:
    """Compare configs without exposing secret values."""
    keys = set(a.keys()) | set(b.keys())
    diff: dict = {"added": {}, "removed": {}, "changed": {}}
    for key in sorted(keys):
        if key in {"secrets", "secret_refs", "api_keys", "credentials"}:
            if a.get(key) != b.get(key):
                diff["changed"][key] = "[REDACTED]"
            continue
        if key not in a:
            diff["added"][key] = b[key]
        elif key not in b:
            diff["removed"][key] = a[key]
        elif a[key] != b[key]:
            diff["changed"][key] = {"from": a[key], "to": b[key]}
    return diff


class ConfigurationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def next_version(self, environment_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.max(ConfigurationVersion.version)).where(
                ConfigurationVersion.environment_id == environment_id
            )
        )
        current = result.scalar_one_or_none()
        return (current or 0) + 1

    async def create_version(
        self,
        environment: Environment,
        config: dict,
        *,
        secret_refs: dict | None = None,
        change_summary: str | None = None,
        author_id: uuid.UUID | None = None,
        activate: bool = False,
    ) -> ConfigurationVersion:
        version_num = await self.next_version(environment.id)
        if activate:
            await self.db.execute(
                select(ConfigurationVersion).where(
                    ConfigurationVersion.environment_id == environment.id,
                    ConfigurationVersion.is_active == True,  # noqa: E712
                )
            )
            active_rows = await self.db.execute(
                select(ConfigurationVersion).where(
                    ConfigurationVersion.environment_id == environment.id,
                    ConfigurationVersion.is_active == True,  # noqa: E712
                )
            )
            for row in active_rows.scalars().all():
                row.is_active = False

        version = ConfigurationVersion(
            organization_id=environment.organization_id,
            environment_id=environment.id,
            version=version_num,
            config=config,
            secret_refs=secret_refs or {},
            change_summary=change_summary,
            author_id=author_id,
            is_active=activate,
        )
        self.db.add(version)
        await self.db.flush()
        return version

    async def compare_versions(
        self, version_a_id: uuid.UUID, version_b_id: uuid.UUID
    ) -> dict:
        a = await self.db.get(ConfigurationVersion, version_a_id)
        b = await self.db.get(ConfigurationVersion, version_b_id)
        if not a or not b:
            raise ValueError("Version not found")
        return {
            "version_a": a.version,
            "version_b": b.version,
            "diff": safe_diff(a.config or {}, b.config or {}),
        }

    async def rollback(
        self,
        environment: Environment,
        target_version_id: uuid.UUID,
        *,
        author_id: uuid.UUID | None,
    ) -> ConfigurationVersion:
        target = await self.db.get(ConfigurationVersion, target_version_id)
        if not target or target.environment_id != environment.id:
            raise ValueError("Target version not found for environment")
        return await self.create_version(
            environment,
            dict(target.config or {}),
            secret_refs=dict(target.secret_refs or {}),
            change_summary=f"Rollback to version {target.version}",
            author_id=author_id,
            activate=True,
        )

    async def promote(
        self,
        source_env: Environment,
        target_env: Environment,
        *,
        author_id: uuid.UUID | None,
        require_approval: bool = False,
    ) -> ConfigurationVersion:
        if require_approval and target_env.is_protected:
            raise ValueError("Protected environment requires approval before promotion")
        expected = PROMOTION_CHAIN.get(source_env.kind)
        if expected and target_env.kind != expected and target_env.kind != EnvironmentKind.CUSTOM:
            raise ValueError(f"Invalid promotion path: {source_env.kind} -> {target_env.kind}")

        active = await self.db.execute(
            select(ConfigurationVersion).where(
                ConfigurationVersion.environment_id == source_env.id,
                ConfigurationVersion.is_active == True,  # noqa: E712
            )
        )
        source_version = active.scalar_one_or_none()
        if not source_version:
            raise ValueError("No active configuration on source environment")

        return await self.create_version(
            target_env,
            dict(source_version.config or {}),
            secret_refs=dict(source_version.secret_refs or {}),
            change_summary=f"Promoted from {source_env.slug} v{source_version.version}",
            author_id=author_id,
            activate=False,
        )

    async def deploy(
        self,
        *,
        org_id: uuid.UUID,
        config_version: ConfigurationVersion,
        environment_id: uuid.UUID | None = None,
        instance_id: uuid.UUID | None = None,
        deployed_by: uuid.UUID | None = None,
        idempotency_key: str | None = None,
    ) -> ConfigurationDeployment:
        if idempotency_key:
            existing = await self.db.execute(
                select(ConfigurationDeployment).where(
                    ConfigurationDeployment.organization_id == org_id,
                    ConfigurationDeployment.idempotency_key == idempotency_key,
                )
            )
            found = existing.scalar_one_or_none()
            if found:
                return found

        deployment = ConfigurationDeployment(
            organization_id=org_id,
            environment_id=environment_id,
            instance_id=instance_id,
            configuration_version_id=config_version.id,
            status=DeploymentStatus.DEPLOYING,
            idempotency_key=idempotency_key,
            deployed_by=deployed_by,
        )
        self.db.add(deployment)
        await self.db.flush()

        # Simulated verify step — real instance would report back via control-plane API
        deployment.status = DeploymentStatus.SUCCESS
        deployment.verified_at = datetime.now(UTC)
        deployment.completed_at = datetime.now(UTC)
        config_version.is_active = True
        record_config_deployment(deployment.status)
        await self.db.flush()
        return deployment
