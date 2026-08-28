"""Organization context resolution and membership checks."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user, verify_token
from app.db.base import get_db
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember, OrganizationRole
from app.models.user import User

security = HTTPBearer(auto_error=False)


@dataclass
class OrgContext:
    user: User
    organization: Organization
    organization_id: uuid.UUID
    role: OrganizationRole
    membership: OrganizationMember


async def _resolve_org_id(
    user: User,
    db: AsyncSession,
    credentials: HTTPAuthorizationCredentials | None,
    header_org_id: str | None,
) -> uuid.UUID:
    org_id: uuid.UUID | None = None

    if credentials:
        try:
            payload = verify_token(credentials.credentials)
            claim = payload.get("org_id")
            if claim:
                org_id = uuid.UUID(str(claim))
        except HTTPException:
            pass

    if header_org_id and org_id is None:
        try:
            org_id = uuid.UUID(header_org_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid X-Organization-ID header")

    if org_id is None:
        org_id = user.organization_id

    if org_id is None:
        raise HTTPException(status_code=400, detail="No active organization")

    return org_id


async def get_membership(
    db: AsyncSession, user_id: uuid.UUID, organization_id: uuid.UUID
) -> OrganizationMember | None:
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


async def get_org_context(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> OrgContext:
    org_id = await _resolve_org_id(user, db, credentials, None)

    membership = await get_membership(db, user.id, org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return OrgContext(
        user=user,
        organization=org,
        organization_id=org_id,
        role=membership.role,
        membership=membership,
    )


async def get_org_context_with_header(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    x_organization_id: str | None = Header(default=None, alias="X-Organization-ID"),
) -> OrgContext:
    org_id = await _resolve_org_id(user, db, credentials, x_organization_id)

    membership = await get_membership(db, user.id, org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return OrgContext(
        user=user,
        organization=org,
        organization_id=org_id,
        role=membership.role,
        membership=membership,
    )


def ensure_same_org(resource_org_id: uuid.UUID | None, ctx: OrgContext) -> None:
    if resource_org_id is None or resource_org_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Resource not found")
