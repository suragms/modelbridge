"""Scoped configuration with deterministic precedence."""

from __future__ import annotations

import uuid
from copy import deepcopy

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud import ConfigScope, ScopedConfiguration

SCOPE_PRECEDENCE = [
    ConfigScope.GLOBAL,
    ConfigScope.ORGANIZATION,
    ConfigScope.WORKSPACE,
    ConfigScope.PROJECT,
    ConfigScope.ENVIRONMENT,
]


class ConfigScopeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def next_version(self, scope: str, scope_ref_id: uuid.UUID | None) -> int:
        result = await self.db.execute(
            select(func.max(ScopedConfiguration.version)).where(
                ScopedConfiguration.scope == scope,
                ScopedConfiguration.scope_ref_id == scope_ref_id,
            )
        )
        current = result.scalar_one_or_none()
        return (current or 0) + 1

    async def create_version(
        self,
        *,
        scope: str,
        scope_ref_id: uuid.UUID | None,
        organization_id: uuid.UUID | None,
        config: dict,
        change_summary: str | None = None,
        author_id: uuid.UUID | None = None,
        activate: bool = False,
    ) -> ScopedConfiguration:
        version_num = await self.next_version(scope, scope_ref_id)
        if activate:
            active_rows = await self.db.execute(
                select(ScopedConfiguration).where(
                    ScopedConfiguration.scope == scope,
                    ScopedConfiguration.scope_ref_id == scope_ref_id,
                    ScopedConfiguration.is_active == True,  # noqa: E712
                )
            )
            for row in active_rows.scalars().all():
                row.is_active = False

        entry = ScopedConfiguration(
            organization_id=organization_id,
            scope=scope,
            scope_ref_id=scope_ref_id,
            version=version_num,
            config=config,
            is_active=activate,
            change_summary=change_summary,
            author_id=author_id,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def resolve(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        workspace_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        environment_id: uuid.UUID | None = None,
    ) -> dict:
        """Merge configs from GLOBAL → ORG → WORKSPACE → PROJECT → ENVIRONMENT."""
        merged: dict = {}
        layers: list[tuple[str, uuid.UUID | None]] = [
            (ConfigScope.GLOBAL, None),
        ]
        if organization_id:
            layers.append((ConfigScope.ORGANIZATION, organization_id))
        if workspace_id:
            layers.append((ConfigScope.WORKSPACE, workspace_id))
        if project_id:
            layers.append((ConfigScope.PROJECT, project_id))
        if environment_id:
            layers.append((ConfigScope.ENVIRONMENT, environment_id))

        for scope, ref_id in layers:
            active = await self.db.execute(
                select(ScopedConfiguration).where(
                    ScopedConfiguration.scope == scope,
                    ScopedConfiguration.scope_ref_id == ref_id,
                    ScopedConfiguration.is_active == True,  # noqa: E712
                )
            )
            cfg = active.scalar_one_or_none()
            if cfg and cfg.config:
                merged = deepcopy_merge(merged, cfg.config)
        return merged


def deepcopy_merge(base: dict, overlay: dict) -> dict:
    result = deepcopy(base)
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deepcopy_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result
