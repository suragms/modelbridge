from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.encryption import hash_api_key
from app.auth.jwt import create_access_token, get_current_user
from app.auth.org_context import OrgContext, ensure_same_org, get_org_context_with_header
from app.auth.rbac import Permission, require_permission
from app.config import get_settings
from app.db.base import get_db
from app.models.organization import Organization
from app.models.organization_invite import OrganizationInvite
from app.models.organization_member import OrganizationMember, OrganizationRole
from app.models.organization_settings import OrganizationSettings
from app.models.user import User
from app.schemas.organization import (
    BudgetAlertResponse,
    JobRunResponse,
    OrganizationCreate,
    OrganizationInviteCreate,
    OrganizationInviteResponse,
    OrganizationMemberResponse,
    OrganizationMemberUpdate,
    OrganizationResponse,
    OrganizationSettingsResponse,
    OrganizationSettingsUpdate,
    OrganizationUpdate,
)
from app.schemas.user import TokenResponse, UserResponse
from app.services.audit import AuditService
from app.utils.slug import unique_slug

router = APIRouter(prefix="/organizations", tags=["Organizations"])

AUDIT_ORG_CREATED = "organization.created"
AUDIT_ORG_UPDATED = "organization.updated"
AUDIT_ORG_DELETED = "organization.deleted"
AUDIT_MEMBER_ADDED = "member.added"
AUDIT_MEMBER_REMOVED = "member.removed"
AUDIT_MEMBER_ROLE_CHANGED = "member.role_changed"
AUDIT_SETTINGS_UPDATED = "settings.updated"
AUDIT_BUDGET_CHANGED = "budget.changed"
AUDIT_QUOTA_CHANGED = "quota.changed"


async def _org_response(db: AsyncSession, org: Organization, user_id: uuid.UUID) -> OrganizationResponse:
    membership = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == user_id,
        )
    )
    member = membership.scalar_one_or_none()
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        created_at=org.created_at,
        updated_at=org.updated_at,
        role=member.role.value if member else None,
    )


@router.get("/", response_model=list[OrganizationResponse])
async def list_organizations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Organization)
        .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
        .where(OrganizationMember.user_id == user.id)
        .order_by(Organization.name)
    )
    orgs = result.scalars().unique().all()
    out: list[OrganizationResponse] = []
    for org in orgs:
        out.append(await _org_response(db, org, user.id))
    return out


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    slug = await unique_slug(db, payload.name)
    org = Organization(name=payload.name, slug=slug, description=payload.description)
    db.add(org)
    await db.flush()

    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role=OrganizationRole.OWNER))
    db.add(OrganizationSettings(organization_id=org.id))
    await db.flush()

    audit = AuditService(db)
    await audit.log(
        AUDIT_ORG_CREATED, "organization", str(org.id),
        actor=user, organization_id=org.id, metadata={"name": org.name, "slug": slug},
    )
    return await _org_response(db, org, user.id)


@router.get("/current", response_model=OrganizationResponse)
async def get_current_organization(ctx: OrgContext = Depends(get_org_context_with_header)):
    return OrganizationResponse(
        id=ctx.organization.id,
        name=ctx.organization.name,
        slug=ctx.organization.slug,
        description=ctx.organization.description,
        created_at=ctx.organization.created_at,
        updated_at=ctx.organization.updated_at,
        role=ctx.role.value,
    )


@router.patch("/current", response_model=OrganizationResponse)
async def update_current_organization(
    payload: OrganizationUpdate,
    ctx: OrgContext = Depends(require_permission(Permission.ORG_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    org = ctx.organization
    if payload.name is not None:
        org.name = payload.name
        org.slug = await unique_slug(db, payload.name, exclude_id=org.id)
    if payload.description is not None:
        org.description = payload.description
    await db.flush()
    audit = AuditService(db)
    await audit.log(
        AUDIT_ORG_UPDATED, "organization", str(org.id),
        actor=ctx.user, organization_id=org.id,
    )
    return await _org_response(db, org, ctx.user.id)


@router.post("/current/switch", response_model=TokenResponse)
async def switch_organization(
    organization_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    membership = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user.id,
        )
    )
    if not membership.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    user.organization_id = organization_id
    await db.flush()

    token = create_access_token({"sub": str(user.id), "email": user.email, "org_id": str(organization_id)})
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.delete("/current", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_organization(
    ctx: OrgContext = Depends(require_permission(Permission.ORG_DELETE)),
    db: AsyncSession = Depends(get_db),
):
    audit = AuditService(db)
    await audit.log(
        AUDIT_ORG_DELETED, "organization", str(ctx.organization.id),
        actor=ctx.user, organization_id=ctx.organization.id,
    )
    await db.delete(ctx.organization)
    await db.flush()


# --- Members ---

@router.get("/current/members", response_model=list[OrganizationMemberResponse])
async def list_members(
    ctx: OrgContext = Depends(require_permission(Permission.MEMBERS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id)
        .where(OrganizationMember.organization_id == ctx.organization_id)
        .order_by(OrganizationMember.created_at)
    )
    rows = result.all()
    return [
        OrganizationMemberResponse(
            id=m.id,
            user_id=m.user_id,
            email=u.email,
            full_name=u.full_name,
            role=m.role.value,
            created_at=m.created_at,
        )
        for m, u in rows
    ]


@router.patch("/current/members/{member_id}", response_model=OrganizationMemberResponse)
async def update_member_role(
    member_id: uuid.UUID,
    payload: OrganizationMemberUpdate,
    ctx: OrgContext = Depends(require_permission(Permission.MEMBERS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        new_role = OrganizationRole(payload.role.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")

    result = await db.execute(
        select(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id)
        .where(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == ctx.organization_id,
        )
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Member not found")
    member, user = row

    if member.role == OrganizationRole.OWNER and new_role != OrganizationRole.OWNER:
        owners = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == ctx.organization_id,
                OrganizationMember.role == OrganizationRole.OWNER,
            )
        )
        if len(owners.scalars().all()) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last owner")

    old_role = member.role.value
    member.role = new_role
    user.role = new_role  # legacy field sync
    await db.flush()

    audit = AuditService(db)
    await audit.log(
        AUDIT_MEMBER_ROLE_CHANGED, "member", str(member.user_id),
        actor=ctx.user, organization_id=ctx.organization_id,
        metadata={"from": old_role, "to": new_role.value},
    )
    return OrganizationMemberResponse(
        id=member.id,
        user_id=member.user_id,
        email=user.email,
        full_name=user.full_name,
        role=member.role.value,
        created_at=member.created_at,
    )


@router.delete("/current/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    member_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.MEMBERS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == ctx.organization_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    if member.user_id == ctx.user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")
    if member.role == OrganizationRole.OWNER:
        raise HTTPException(status_code=400, detail="Transfer ownership before removing owner")

    audit = AuditService(db)
    await audit.log(
        AUDIT_MEMBER_REMOVED, "member", str(member.user_id),
        actor=ctx.user, organization_id=ctx.organization_id,
    )
    await db.delete(member)
    await db.flush()


# --- Invites (token-based; no email delivery) ---

@router.post("/current/invites", response_model=OrganizationInviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    payload: OrganizationInviteCreate,
    ctx: OrgContext = Depends(require_permission(Permission.MEMBERS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        role = OrganizationRole(payload.role.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")

    raw_token = secrets.token_urlsafe(32)
    invite = OrganizationInvite(
        organization_id=ctx.organization_id,
        token_hash=hash_api_key(raw_token),
        role=role,
        email_hint=payload.email_hint,
        expires_at=datetime.now(UTC) + timedelta(days=payload.expires_in_days),
        created_by_id=ctx.user.id,
    )
    db.add(invite)
    await db.flush()

    settings = get_settings()
    base = settings.cors_origins[0] if settings.cors_origins else "http://localhost:3000"
    invite_url = f"{base}/register?invite={raw_token}"

    audit = AuditService(db)
    await audit.log(
        AUDIT_MEMBER_ADDED, "invite", str(invite.id),
        actor=ctx.user, organization_id=ctx.organization_id,
        metadata={"role": role.value, "email_hint": payload.email_hint},
    )

    return OrganizationInviteResponse(
        id=invite.id,
        role=role.value,
        email_hint=payload.email_hint,
        expires_at=invite.expires_at,
        invite_url=invite_url,
        token=raw_token,
    )


@router.post("/invites/accept")
async def accept_invite(
    token: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    token_hash = hash_api_key(token)
    result = await db.execute(
        select(OrganizationInvite).where(
            OrganizationInvite.token_hash == token_hash,
            OrganizationInvite.accepted_at.is_(None),
        )
    )
    invite = result.scalar_one_or_none()
    if not invite or invite.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=400, detail="Invalid or expired invite")

    existing = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == invite.organization_id,
            OrganizationMember.user_id == user.id,
        )
    )
    if not existing.scalar_one_or_none():
        db.add(
            OrganizationMember(
                organization_id=invite.organization_id,
                user_id=user.id,
                role=invite.role,
            )
        )

    invite.accepted_at = datetime.now(UTC)
    user.organization_id = invite.organization_id
    await db.flush()

    access_token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "org_id": str(invite.organization_id),
    })
    return TokenResponse(access_token=access_token, user=UserResponse.model_validate(user))


# --- Settings ---

@router.get("/current/settings", response_model=OrganizationSettingsResponse)
async def get_settings_route(
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrganizationSettings).where(
            OrganizationSettings.organization_id == ctx.organization_id
        )
    )
    settings = result.scalar_one_or_none()
    if not settings:
        settings = OrganizationSettings(organization_id=ctx.organization_id)
        db.add(settings)
        await db.flush()
    return OrganizationSettingsResponse.model_validate(settings)


@router.patch("/current/settings", response_model=OrganizationSettingsResponse)
async def update_settings(
    payload: OrganizationSettingsUpdate,
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrganizationSettings).where(
            OrganizationSettings.organization_id == ctx.organization_id
        )
    )
    settings = result.scalar_one_or_none()
    if not settings:
        settings = OrganizationSettings(organization_id=ctx.organization_id)
        db.add(settings)
        await db.flush()

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(settings, key, value)
    await db.flush()

    audit = AuditService(db)
    if any(k in data for k in ("monthly_budget_usd", "budget_warning_percent", "budget_hard_limit_percent")):
        await audit.log(AUDIT_BUDGET_CHANGED, "organization_settings", str(settings.organization_id), actor=ctx.user, organization_id=ctx.organization_id, metadata=data)
    if "monthly_token_limit" in data:
        await audit.log(AUDIT_QUOTA_CHANGED, "organization_settings", str(settings.organization_id), actor=ctx.user, organization_id=ctx.organization_id, metadata=data)
    await audit.log(AUDIT_SETTINGS_UPDATED, "organization_settings", str(settings.organization_id), actor=ctx.user, organization_id=ctx.organization_id, metadata=data)

    return OrganizationSettingsResponse.model_validate(settings)


@router.get("/current/budget-alerts", response_model=list[BudgetAlertResponse])
async def list_budget_alerts(
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    from app.models.budget_alert import BudgetAlert

    result = await db.execute(
        select(BudgetAlert)
        .where(BudgetAlert.organization_id == ctx.organization_id)
        .order_by(BudgetAlert.created_at.desc())
        .limit(50)
    )
    return [BudgetAlertResponse.model_validate(a) for a in result.scalars().all()]


@router.get("/current/jobs", response_model=list[JobRunResponse])
async def list_job_runs(
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    from app.models.job_run import JobRun

    result = await db.execute(
        select(JobRun).order_by(JobRun.started_at.desc()).limit(50)
    )
    return [JobRunResponse.model_validate(j) for j in result.scalars().all()]
