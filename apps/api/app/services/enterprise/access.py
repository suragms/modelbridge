"""Enterprise workspace and project access control."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enterprise import (
    Project,
    ProjectMember,
    ProjectRole,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)
from app.models.organization_member import OrganizationRole

WORKSPACE_ROLE_RANK = {
    WorkspaceRole.VIEWER: 1,
    WorkspaceRole.MEMBER: 2,
    WorkspaceRole.ADMIN: 3,
    WorkspaceRole.OWNER: 4,
}

PROJECT_ROLE_RANK = {
    ProjectRole.VIEWER: 1,
    ProjectRole.MEMBER: 2,
    ProjectRole.ADMIN: 3,
}


def org_role_can_manage_enterprise(role: OrganizationRole) -> bool:
    return role in {OrganizationRole.OWNER, OrganizationRole.ADMIN}


async def get_workspace(
    db: AsyncSession, org_id: uuid.UUID, workspace_id: uuid.UUID
) -> Workspace:
    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.organization_id == org_id)
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


async def get_project(db: AsyncSession, org_id: uuid.UUID, project_id: uuid.UUID) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.organization_id == org_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def workspace_role(
    db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> str | None:
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    return member.role if member else None


async def project_role(db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    return member.role if member else None


async def assert_workspace_access(
    db: AsyncSession,
    workspace: Workspace,
    user_id: uuid.UUID,
    org_role: OrganizationRole,
    *,
    min_role: str = WorkspaceRole.VIEWER,
) -> None:
    if org_role_can_manage_enterprise(org_role):
        return
    role = await workspace_role(db, workspace.id, user_id)
    if not role or WORKSPACE_ROLE_RANK.get(role, 0) < WORKSPACE_ROLE_RANK.get(min_role, 0):
        raise HTTPException(status_code=403, detail="Workspace access denied")


async def assert_project_access(
    db: AsyncSession,
    project: Project,
    user_id: uuid.UUID,
    org_role: OrganizationRole,
    *,
    min_role: str = ProjectRole.VIEWER,
) -> None:
    if org_role_can_manage_enterprise(org_role):
        return
    ws_role = await workspace_role(db, project.workspace_id, user_id)
    if not ws_role:
        raise HTTPException(status_code=403, detail="Project access denied")
    if project.is_restricted:
        p_role = await project_role(db, project.id, user_id)
        if not p_role or PROJECT_ROLE_RANK.get(p_role, 0) < PROJECT_ROLE_RANK.get(min_role, 0):
            raise HTTPException(status_code=403, detail="Restricted project access denied")
    elif WORKSPACE_ROLE_RANK.get(ws_role, 0) < WORKSPACE_ROLE_RANK.get(WorkspaceRole.VIEWER, 0):
        raise HTTPException(status_code=403, detail="Project access denied")
