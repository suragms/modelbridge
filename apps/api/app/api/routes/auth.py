from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token, get_current_user
from app.auth.password import hash_password, verify_password
from app.db.base import get_db
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember, OrganizationRole
from app.models.organization_settings import OrganizationSettings
from app.models.user import User, UserRole
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse
from app.services.audit import AUDIT_USER_LOGIN, AuditService
from app.utils.slug import unique_slug

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    org = Organization(name=f"{payload.email}'s Organization", slug=await unique_slug(db, payload.email))
    db.add(org)
    await db.flush()

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.OWNER.value,
        organization_id=org.id,
    )
    db.add(user)
    await db.flush()

    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role=OrganizationRole.OWNER.value))
    db.add(OrganizationSettings(organization_id=org.id))
    await db.flush()

    token = create_access_token({"sub": str(user.id), "email": user.email, "org_id": str(org.id)})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    token = create_access_token({"sub": str(user.id), "email": user.email, "org_id": str(user.organization_id) if user.organization_id else None})
    audit = AuditService(db)
    await audit.log(AUDIT_USER_LOGIN, "user", str(user.id), actor=user)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)
