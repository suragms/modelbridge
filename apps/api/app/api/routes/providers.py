from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.encryption import decrypt_secret, encrypt_secret
from app.auth.jwt import get_current_user
from app.db.base import get_db
from app.models.model import Model
from app.models.provider import Provider, ProviderCredential
from app.models.user import User
from app.services.health import HealthService
from app.schemas.provider import (
    ProviderCreate,
    ProviderResponse,
    ProviderTestResult,
    ProviderUpdate,
)
from app.utils.urls import InvalidURL, validate_provider_url

router = APIRouter(prefix="/providers", tags=["Providers"])


async def _get_owned_provider(db: AsyncSession, provider_id: uuid.UUID, user: User) -> Provider:
    """Fetch a provider scoped to the requesting user's organization."""
    result = await db.execute(
        select(Provider).where(
            Provider.id == provider_id, Provider.organization_id == user.organization_id
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


async def _decrypt_provider_key(db: AsyncSession, provider: Provider) -> str | None:
    cred_result = await db.execute(
        select(ProviderCredential).where(ProviderCredential.provider_id == provider.id)
    )
    cred = cred_result.scalar_one_or_none()
    if not cred:
        return None
    return decrypt_secret(cred.encrypted_key)


def _validated_base_url(base_url: str | None, provider_type: str) -> str | None:
    """Validate a provider URL against the provider type; reject unsafe URLs."""
    try:
        return validate_provider_url(base_url, provider_type)
    except InvalidURL as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    payload: ProviderCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base_url = _validated_base_url(payload.base_url, payload.type)
    provider = Provider(
        name=payload.name,
        type=payload.type,
        base_url=base_url,
        config=payload.config,
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

    return ProviderResponse.model_validate_from_provider(provider)


@router.get("/", response_model=list[ProviderResponse])
async def list_providers(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Provider).where(Provider.organization_id == user.organization_id)
    )
    providers = result.scalars().all()
    return [ProviderResponse.model_validate_from_provider(p) for p in providers]


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = await _get_owned_provider(db, provider_id, user)
    return ProviderResponse.model_validate_from_provider(provider)


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: uuid.UUID,
    payload: ProviderUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = await _get_owned_provider(db, provider_id, user)

    if payload.name is not None:
        provider.name = payload.name
    if payload.base_url is not None:
        provider.base_url = _validated_base_url(payload.base_url, provider.type)
    if payload.is_enabled is not None:
        provider.is_enabled = payload.is_enabled
    if payload.config is not None:
        provider.config = payload.config

    if payload.api_key:
        # Replace existing credentials (never leave a stale key behind).
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

    await db.flush()
    return ProviderResponse.model_validate_from_provider(provider)


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = await _get_owned_provider(db, provider_id, user)
    await db.delete(provider)
    await db.flush()


@router.post("/{provider_id}/test", response_model=ProviderTestResult)
async def test_provider(
    provider_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = await _get_owned_provider(db, provider_id, user)
    api_key = await _decrypt_provider_key(db, provider)

    health = HealthService(db)
    result = await health.check_provider(provider, api_key)
    return ProviderTestResult(
        success=result["success"],
        message=result["message"],
        latency_ms=result.get("latency_ms"),
    )


@router.post("/{provider_id}/discover-models", response_model=list[dict])
async def discover_models(
    provider_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = await _get_owned_provider(db, provider_id, user)
    api_key = await _decrypt_provider_key(db, provider)

    from app.providers.registry import get_provider_registry

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

    discovered = []
    for pm in provider_models:
        existing = await db.execute(
            select(Model).where(
                Model.provider_model_id == pm.id,
                Model.provider_id == provider.id,
            )
        )
        current = existing.scalar_one_or_none()
        if current:
            discovered.append({"id": pm.id, "name": pm.name, "status": "exists"})
        else:
            discovered.append({"id": pm.id, "name": pm.name, "status": "added"})

    await db.flush()
    return discovered


@router.post("/{provider_id}/models/sync", response_model=list[dict])
async def sync_models(
    provider_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Refresh the model registry from the provider's live model list.

    Adds models not yet registered, updates details of known models, and marks
    previously-registered models that no longer appear as unavailable (disabled).
    Discovered capabilities come from the provider; nothing is fabricated.
    """
    provider = await _get_owned_provider(db, provider_id, user)
    api_key = await _decrypt_provider_key(db, provider)

    from app.providers.registry import get_provider_registry

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

    from datetime import UTC, datetime

    now = datetime.now(UTC)
    seen_ids: set[str] = set()
    result: list[dict] = []

    for pm in provider_models:
        seen_ids.add(pm.id)
        existing_result = await db.execute(
            select(Model).where(
                Model.provider_model_id == pm.id,
                Model.provider_id == provider.id,
            )
        )
        current = existing_result.scalar_one_or_none()

        if current:
            current.display_name = pm.name or current.display_name
            current.context_window = pm.context_window or current.context_window
            current.input_price_per_1k = pm.input_price_per_1k
            current.output_price_per_1k = pm.output_price_per_1k
            current.supports_streaming = pm.supports_streaming
            current.supports_tools = pm.supports_tools
            current.supports_embeddings = pm.supports_embeddings
            current.supports_vision = pm.supports_vision
            current.supports_json_mode = pm.supports_json_mode
            current.quality_score = pm.quality_score
            current.is_enabled = True
            current.last_synced_at = now
            result.append({"id": pm.id, "name": pm.name, "status": "updated"})
        else:
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
                is_enabled=True,
                last_synced_at=now,
            )
            db.add(model)
            result.append({"id": pm.id, "name": pm.name, "status": "added"})

    # Disable previously-known models that disappeared from the live list.
    registered_result = await db.execute(
        select(Model).where(Model.provider_id == provider.id)
    )
    for registered in registered_result.scalars().all():
        if registered.provider_model_id not in seen_ids and registered.is_enabled:
            registered.is_enabled = False
            registered.last_synced_at = now
            result.append(
                {
                    "id": registered.provider_model_id,
                    "name": registered.display_name,
                    "status": "unavailable",
                }
            )

    await db.flush()
    return result
