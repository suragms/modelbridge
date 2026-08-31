"""Workspace APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.org_context import OrgContext
from app.auth.rbac import Permission, require_permission
from app.db.base import get_db
from app.models.enterprise import (
    Project,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
    WorkspaceStatus,
)
from app.schemas.enterprise import (
    WorkspaceCreate,
    WorkspaceMemberAdd,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from app.services.enterprise.access import assert_workspace_access, get_workspace
from app.services.enterprise.activity import record_activity

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


def _workspace_response(ws: Workspace, project_count: int = 0, member_count: int = 0) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=ws.id,
        organization_id=ws.organization_id,
        name=ws.name,
        description=ws.description,
        status=ws.status,
        created_by=ws.created_by,
        created_at=ws.created_at,
        updated_at=ws.updated_at,
        project_count=project_count,
        member_count=member_count,
    )


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    ctx: OrgContext = Depends(require_permission(Permission.ENTERPRISE_READ)),
    db: AsyncSession = Depends(get_db),
):
    if ctx.role.value in {"owner", "admin"}:
        result = await db.execute(
            select(Workspace).where(
                Workspace.organization_id == ctx.organization_id,
                Workspace.status == WorkspaceStatus.ACTIVE,
            )
        )
        workspaces = list(result.scalars().all())
    else:
        result = await db.execute(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(
                Workspace.organization_id == ctx.organization_id,
                WorkspaceMember.user_id == ctx.user.id,
                Workspace.status == WorkspaceStatus.ACTIVE,
            )
        )
        workspaces = list(result.scalars().unique().all())

    out: list[WorkspaceResponse] = []
    for ws in workspaces:
        pc = await db.scalar(select(func.count()).select_from(Project).where(Project.workspace_id == ws.id))
        mc = await db.scalar(
            select(func.count()).select_from(WorkspaceMember).where(WorkspaceMember.workspace_id == ws.id)
        )
        out.append(_workspace_response(ws, pc or 0, mc or 0))
    return out


@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    payload: WorkspaceCreate,
    ctx: OrgContext = Depends(require_permission(Permission.ENTERPRISE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    ws = Workspace(
        organization_id=ctx.organization_id,
        name=payload.name,
        description=payload.description,
        created_by=ctx.user.id,
    )
    db.add(ws)
    await db.flush()
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=ctx.user.id, role=WorkspaceRole.OWNER))
    await record_activity(
        db,
        organization_id=ctx.organization_id,
        workspace_id=ws.id,
        event_type="workspace.created",
        resource_type="workspace",
        resource_id=str(ws.id),
        actor_id=ctx.user.id,
    )
    await db.commit()
    await db.refresh(ws)
    return _workspace_response(ws, 0, 1)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace_detail(
    workspace_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.ENTERPRISE_READ)),
    db: AsyncSession = Depends(get_db),
):
    ws = await get_workspace(db, ctx.organization_id, workspace_id)
    await assert_workspace_access(db, ws, ctx.user.id, ctx.role)
    pc = await db.scalar(select(func.count()).select_from(Project).where(Project.workspace_id == ws.id))
    mc = await db.scalar(
        select(func.count()).select_from(WorkspaceMember).where(WorkspaceMember.workspace_id == ws.id)
    )
    return _workspace_response(ws, pc or 0, mc or 0)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    ctx: OrgContext = Depends(require_permission(Permission.ENTERPRISE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    ws = await get_workspace(db, ctx.organization_id, workspace_id)
    await assert_workspace_access(db, ws, ctx.user.id, ctx.role, min_role=WorkspaceRole.ADMIN)
    for key, val in payload.model_dump(exclude_unset=True).items():
        setattr(ws, key, val)
    await record_activity(
        db,
        organization_id=ctx.organization_id,
        workspace_id=ws.id,
        event_type="workspace.updated",
        actor_id=ctx.user.id,
    )
    await db.commit()
    await db.refresh(ws)
    return _workspace_response(ws)


@router.post("/{workspace_id}/members", status_code=201)
async def add_workspace_member(
    workspace_id: uuid.UUID,
    payload: WorkspaceMemberAdd,
    ctx: OrgContext = Depends(require_permission(Permission.ENTERPRISE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    ws = await get_workspace(db, ctx.organization_id, workspace_id)
    await assert_workspace_access(db, ws, ctx.user.id, ctx.role, min_role=WorkspaceRole.ADMIN)
    if payload.role not in {r.value for r in WorkspaceRole}:
        raise HTTPException(status_code=400, detail="Invalid role")
    existing = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == ws.id,
            WorkspaceMember.user_id == payload.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already a member")
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=payload.user_id, role=payload.role))
    await db.commit()
    return {"status": "ok"}
