from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.encryption import generate_api_key, get_key_prefix, hash_api_key
from app.auth.org_context import OrgContext, ensure_same_org
from app.auth.rbac import Permission, require_permission
from app.db.base import get_db
from app.models.api_key import ALL_API_KEY_SCOPES, APIKey
from app.schemas.api_key import APIKeyCreate, APIKeyCreated, APIKeyResponse
from app.services.audit import AUDIT_API_KEY_CREATED, AUDIT_API_KEY_REVOKED, AuditService

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


def _validate_scopes(scopes: list[str]) -> list[str]:
    if not scopes:
        return []
    invalid = [s for s in scopes if s not in ALL_API_KEY_SCOPES]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid scopes: {', '.join(invalid)}")
    return scopes


@router.post("/", response_model=APIKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: APIKeyCreate,
    ctx: OrgContext = Depends(require_permission(Permission.KEYS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    scopes = _validate_scopes(payload.scopes)

    expires_at = None
    if payload.expires_in_days:
        expires_at = datetime.now(UTC) + timedelta(days=payload.expires_in_days)

    api_key = APIKey(
        key_hash=key_hash,
        key_prefix=get_key_prefix(raw_key),
        name=payload.name,
        scopes=scopes,
        expires_at=expires_at,
        monthly_token_limit=payload.monthly_token_limit,
        monthly_budget_usd=payload.monthly_budget_usd,
        user_id=ctx.user.id,
        organization_id=ctx.organization_id,
        created_by_id=ctx.user.id,
    )
    db.add(api_key)
    await db.flush()

    audit = AuditService(db)
    await audit.log(
        AUDIT_API_KEY_CREATED, "api_key", str(api_key.id),
        actor=ctx.user, organization_id=ctx.organization_id,
        metadata={"name": payload.name, "prefix": api_key.key_prefix, "scopes": api_key.effective_scopes()},
    )

    return APIKeyCreated(
        id=api_key.id,
        key=raw_key,
        key_prefix=api_key.key_prefix,
        name=api_key.name,
        scopes=api_key.effective_scopes(),
        created_at=api_key.created_at,
    )


@router.get("/", response_model=list[APIKeyResponse])
async def list_api_keys(
    ctx: OrgContext = Depends(require_permission(Permission.KEYS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(APIKey)
        .where(APIKey.organization_id == ctx.organization_id, APIKey.is_active == True)  # noqa: E712
        .order_by(APIKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [
        APIKeyResponse(
            id=k.id,
            key_prefix=k.key_prefix,
            name=k.name,
            is_active=k.is_active,
            scopes=k.effective_scopes(),
            expires_at=k.expires_at,
            monthly_token_limit=k.monthly_token_limit,
            monthly_budget_usd=k.monthly_budget_usd,
            created_at=k.created_at,
            last_used_at=k.last_used_at,
        )
        for k in keys
    ]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.KEYS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    ensure_same_org(api_key.organization_id, ctx)

    api_key.is_active = False
    audit = AuditService(db)
    await audit.log(
        AUDIT_API_KEY_REVOKED, "api_key", str(api_key.id),
        actor=ctx.user, organization_id=ctx.organization_id,
        metadata={"name": api_key.name, "prefix": api_key.key_prefix},
    )
    await db.flush()
