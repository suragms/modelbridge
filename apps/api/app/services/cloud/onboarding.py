"""Cloud onboarding flow with real persistence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud import CloudOnboarding
from app.models.enterprise import (
    Environment,
    EnvironmentKind,
    Project,
    ProjectMember,
    ProjectRole,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)

ONBOARDING_STEPS = [
    "organization",
    "administrator",
    "workspace",
    "project",
    "environment",
    "region",
]


class CloudOnboardingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, organization_id: uuid.UUID) -> CloudOnboarding:
        result = await self.db.execute(
            select(CloudOnboarding).where(CloudOnboarding.organization_id == organization_id)
        )
        record = result.scalar_one_or_none()
        if record:
            return record
        record = CloudOnboarding(
            organization_id=organization_id,
            steps_completed=["organization"],
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def complete_step(
        self,
        record: CloudOnboarding,
        step: str,
        *,
        selected_region_id: uuid.UUID | None = None,
        data_residency_policy: str | None = None,
    ) -> CloudOnboarding:
        if step not in ONBOARDING_STEPS:
            raise ValueError(f"Unknown onboarding step: {step}")
        steps = list(record.steps_completed or [])
        if step not in steps:
            steps.append(step)
        record.steps_completed = steps
        if selected_region_id:
            record.selected_region_id = selected_region_id
        if data_residency_policy:
            record.data_residency_policy = data_residency_policy

        required = set(ONBOARDING_STEPS)
        if required.issubset(set(steps)):
            record.is_complete = True
            record.completed_at = datetime.now(UTC)
        record.updated_at = datetime.now(UTC)
        await self.db.flush()
        return record

    async def bootstrap_workspace(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        workspace_name: str = "Default Workspace",
        project_name: str = "Default Project",
    ) -> dict:
        """Create workspace + project with default environments."""
        workspace = Workspace(
            organization_id=organization_id,
            name=workspace_name,
            created_by=user_id,
        )
        self.db.add(workspace)
        await self.db.flush()
        self.db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user_id, role=WorkspaceRole.OWNER))

        project = Project(
            organization_id=organization_id,
            workspace_id=workspace.id,
            name=project_name,
            created_by=user_id,
        )
        self.db.add(project)
        await self.db.flush()
        self.db.add(ProjectMember(project_id=project.id, user_id=user_id, role=ProjectRole.ADMIN))

        for name, slug, kind, protected in [
            ("Development", "development", EnvironmentKind.DEVELOPMENT, False),
            ("Staging", "staging", EnvironmentKind.STAGING, False),
            ("Production", "production", EnvironmentKind.PRODUCTION, True),
        ]:
            self.db.add(
                Environment(
                    organization_id=organization_id,
                    project_id=project.id,
                    name=name,
                    slug=slug,
                    kind=kind,
                    is_protected=protected,
                )
            )
        await self.db.flush()

        record = await self.get_or_create(organization_id)
        await self.complete_step(record, "workspace")
        await self.complete_step(record, "project")
        await self.complete_step(record, "environment")
        return {
            "workspace_id": str(workspace.id),
            "project_id": str(project.id),
            "onboarding": record,
        }
