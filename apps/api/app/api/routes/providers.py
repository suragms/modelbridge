from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.encryption import decrypt_secret, encrypt_secret
from app.auth.jwt import get_current_user
from app.db.base import get_db
from app.models.model import Model
from app.models.provider import Provider, ProviderCredential, ProviderStatus
from app.models.user import User
from app.providers.registry import get_provider_registry
from app.schemas.provider import (
    ProviderCreate,
    ProviderResponse,
    ProviderTestResult,
    ProviderUpdate,
)

router = APIRouter(prefix="/providers", tags=["Providers"])


@router.post("/", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    payload: ProviderCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = Provider(
        name=payload.name,
        type=payload.type,
        base_url=payload.base_url,
        organization_id=user.organization_id,
    )
    db.add(provider)
    await db.flush()

    if payload.api_key:
        cred = ProviderCredential(
            encrypted_key=encrypt_secret(payload.api_key),
            key_name="default",
            provider_id=provider.id,
        )
        db.add(cred)
        await db.flush()

    return ProviderResponse.model_validate(provider)


@router.get("/", response_model=list[ProviderResponse])
async def list_providers(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Provider).where(Provider.organization_id == user.organization_id)
    )
    providers = result.scalars().all()
    return [ProviderResponse.model_validate(p) for p in providers]


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Provider).where(
            Provider.id == provider_id, Provider.organization_id == user.organization_id
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return ProviderResponse.model_validate(provider)


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: uuid.UUID,
    payload: ProviderUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Provider).where(
            Provider.id == provider_id, Provider.organization_id == user.organization_id
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    if payload.name is not None:
        provider.name = payload.name
    if payload.base_url is not None:
        provider.base_url = payload.base_url
    if payload.is_enabled is not None:
        provider.is_enabled = payload.is_enabled
    if payload.config is not None:
        provider.config = payload.config

    if payload.api_key:
        # Remove old credentials
        old_creds = await db.execute(
            select(ProviderCredential).where(ProviderCredential.provider_id == provider.id)
        )
        for cred in old_creds.scalars().all():
            await db.delete(cred)

        cred = ProviderCredential(
            encrypted_key=encrypt_secret(payload.api_key),
            key_name="default",
            provider_id=provider.id,
        )
        db.add(cred)

    await db.flush()
    return ProviderResponse.model_validate(provider)


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Provider).where(
            Provider.id == provider_id, Provider.organization_id == user.organization_id
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    await db.delete(provider)
    await db.flush()


@router.post("/{provider_id}/test", response_model=ProviderTestResult)
async def test_provider(
    provider_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Provider).where(
            Provider.id == provider_id, Provider.organization_id == user.organization_id
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Get API key
    api_key = None
    cred_result = await db.execute(
        select(ProviderCredential).where(ProviderCredential.provider_id == provider.id)
    )
    cred = cred_result.scalar_one_or_none()
    if cred:
        api_key = decrypt_secret(cred.encrypted_key)

    registry = get_provider_registry()
    try:
        ai_provider = registry.create_provider(
            provider_type=provider.type,
            api_key=api_key,
            base_url=provider.base_url,
        )
    except ValueError as e:
        return ProviderTestResult(success=False, message=str(e))

    start = time.time()
    healthy = await ai_provider.health_check()
    latency = (time.time() - start) * 1000

    if healthy:
        provider.status = ProviderStatus.HEALTHY
    else:
        provider.status = ProviderStatus.OFFLINE
    await db.flush()

    return ProviderTestResult(
        success=healthy,
        message="Provider is healthy" if healthy else "Provider is unreachable",
        latency_ms=latency,
    )


@router.post("/{provider_id}/discover-models", response_model=list[dict])
async def discover_models(
    provider_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Provider).where(
            Provider.id == provider_id, Provider.organization_id == user.organization_id
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    api_key = None
    cred_result = await db.execute(
        select(ProviderCredential).where(ProviderCredential.provider_id == provider.id)
    )
    cred = cred_result.scalar_one_or_none()
    if cred:
        api_key = decrypt_secret(cred.encrypted_key)

    registry = get_provider_registry()
    try:
        ai_provider = registry.create_provider(
            provider_type=provider.type,
            api_key=api_key,
            base_url=provider.base_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    provider_models = await ai_provider.list_models()

    # Sync discovered models to database
    discovered = []
    for pm in provider_models:
        existing = await db.execute(
            select(Model).where(
                Model.provider_model_id == pm.id,
                Model.provider_id == provider.id,
            )
        )
        if not existing.scalar_one_or_none():
            model = Model(
                provider_model_id=pm.id,
                display_name=pm.name,
                context_window=pm.context_window,
                input_price_per_1k=pm.input_price_per_1k,
                output_price_per_1k=pm.output_price_per_1k,
                supports_streaming=pm.supports_streaming,
                supports_tools=pm.supports_tools,
                supports_embeddings=pm.supports_embeddings,
                supports_vision=pm.supports_vision,
                supports_json_mode=pm.supports_json_mode,
                quality_score=pm.quality_score,
                provider_id=provider.id,
            )
            db.add(model)
            discovered.append({"id": pm.id, "name": pm.name, "status": "added"})
        else:
            discovered.append({"id": pm.id, "name": pm.name, "status": "exists"})

    await db.flush()
    return discovered
