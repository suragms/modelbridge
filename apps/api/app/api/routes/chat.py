from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.encryption import decrypt_secret
from app.auth.jwt import get_api_key_or_user
from app.db.base import get_db
from app.models.api_key import APIKey
from app.models.model import Model
from app.models.provider import Provider, ProviderCredential
from app.models.user import User
from app.providers.base import ChatMessage as ProviderChatMessage
from app.providers.registry import get_provider_registry
from app.router.engine import RoutingEngine
from app.schemas.chat import (
    ChatChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ModelInfo,
    ModelListResponse,
    UsageInfo,
)
from app.services.cost import CostService
from app.services.usage import UsageService

router = APIRouter(tags=["OpenAI-Compatible"])

routing_engine = RoutingEngine()


def _provider_messages(messages: list) -> list[ProviderChatMessage]:
    return [
        ProviderChatMessage(
            role=m.role,
            content=m.content,
            name=m.name,
            tool_call_id=m.tool_call_id,
            tool_calls=m.tool_calls,
        )
        for m in messages
    ]


async def _get_provider_for_model(
    model_name: str,
    db: AsyncSession,
) -> tuple[Provider, ProviderCredential | None, str]:
    """Find a provider that can serve this model, or use auto-routing."""
    if model_name == "auto":
        # Auto-route: find all enabled models and pick best
        models_result = await db.execute(
            select(Model).where(Model.is_enabled)
        )
        all_models = list(models_result.scalars().all())
        if not all_models:
            raise HTTPException(status_code=404, detail="No models available")

        provider_ids = list(set(str(m.provider_id) for m in all_models))
        providers_result = await db.execute(
            select(Provider).where(Provider.id.in_(provider_ids), Provider.is_enabled)
        )
        all_providers = list(providers_result.scalars().all())

        decision = routing_engine.route(all_models, all_providers, strategy="balanced")
        if not decision:
            raise HTTPException(status_code=503, detail="No healthy providers available")

        cred_result = await db.execute(
            select(ProviderCredential).where(ProviderCredential.provider_id == decision.provider.id)
        )
        cred = cred_result.scalar_one_or_none()
        return decision.provider, cred, decision.model.provider_model_id

    # Specific model requested
    model_result = await db.execute(
        select(Model).where(Model.provider_model_id == model_name, Model.is_enabled)
    )
    model = model_result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found or disabled")

    provider_result = await db.execute(
        select(Provider).where(Provider.id == model.provider_id, Provider.is_enabled)
    )
    provider = provider_result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=503, detail="Provider not available")

    cred_result = await db.execute(
        select(ProviderCredential).where(ProviderCredential.provider_id == provider.id)
    )
    cred = cred_result.scalar_one_or_none()
    return provider, cred, model_name


async def _get_fallback_providers(
    exclude_provider_id: str,
    db: AsyncSession,
) -> list[tuple[Provider, ProviderCredential | None]]:
    """Get other enabled providers for fallback."""
    result = await db.execute(
        select(Provider).where(
            Provider.is_enabled,
            Provider.id != exclude_provider_id,
        )
    )
    providers = list(result.scalars().all())
    fallbacks = []
    for p in providers:
        cred_result = await db.execute(
            select(ProviderCredential).where(ProviderCredential.provider_id == p.id)
        )
        cred = cred_result.scalar_one_or_none()
        fallbacks.append((p, cred))
    return fallbacks


@router.post("/v1/chat/completions")
async def chat_completions(
    payload: ChatCompletionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    principal: tuple[User | None, APIKey | None] = Depends(get_api_key_or_user),
):
    user, authenticated_key = principal

    if authenticated_key is not None:
        authenticated_key.last_used_at = datetime.now(UTC)

    request_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    start_time = time.time()

    provider, cred, actual_model = await _get_provider_for_model(payload.model, db)
    provider_api_key = decrypt_secret(cred.encrypted_key) if cred else None

    registry = get_provider_registry()
    messages = _provider_messages(payload.messages)

    try:
        ai_provider = registry.create_provider(
            provider_type=provider.type,
            api_key=provider_api_key,
            base_url=provider.base_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    usage_service = UsageService(db)
    cost_service = CostService(db)

    if payload.stream:
        return StreamingResponse(
            _stream_response(
                ai_provider, actual_model, messages, payload, request_id,
                provider.name, user, db, usage_service, cost_service, start_time,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming
    try:
        result = await ai_provider.chat_completion(
            model=actual_model,
            messages=messages,
            temperature=payload.temperature,
            top_p=payload.top_p,
            max_tokens=payload.max_tokens,
            stream=False,
            stop=payload.stop,
            tools=payload.tools,
            tool_choice=payload.tool_choice,
            response_format=payload.response_format,
        )
    except Exception as e:
        latency = (time.time() - start_time) * 1000
        await usage_service.log_request(
            request_id=request_id,
            model=actual_model,
            provider=provider.name,
            latency_ms=latency,
            status="error",
            error=str(e),
            user_id=user.id if user else None,
            organization_id=user.organization_id if user else None,
        )
        raise HTTPException(status_code=502, detail=f"Provider error: {str(e)}")

    latency = (time.time() - start_time) * 1000
    routing_engine.record_latency(actual_model, latency)

    # Log usage
    usage_data = result.usage
    await usage_service.log_request(
        request_id=request_id,
        model=actual_model,
        provider=provider.name,
        latency_ms=latency,
        status="success",
        user_id=user.id if user else None,
        organization_id=user.organization_id if user else None,
    )
    await usage_service.log_usage(
        request_id=request_id,
        model=actual_model,
        provider=provider.name,
        input_tokens=usage_data.get("prompt_tokens", 0),
        output_tokens=usage_data.get("completion_tokens", 0),
        user_id=user.id if user else None,
        organization_id=user.organization_id if user else None,
    )
    await cost_service.estimate_and_log(
        request_id=request_id,
        model_name=actual_model,
        provider_name=provider.name,
        input_tokens=usage_data.get("prompt_tokens", 0),
        output_tokens=usage_data.get("completion_tokens", 0),
        user_id=user.id if user else None,
        organization_id=user.organization_id if user else None,
    )

    choices = []
    for choice_data in result.choices:
        msg = choice_data.get("message", {})
        choices.append(ChatChoice(
            index=choice_data.get("index", 0),
            message={"role": msg.get("role", "assistant"), "content": msg.get("content", "")},
            finish_reason=choice_data.get("finish_reason", "stop"),
        ))

    return ChatCompletionResponse(
        id=result.id,
        created=int(time.time()),
        model=actual_model,
        choices=choices,
        usage=UsageInfo(**usage_data),
    )


async def _stream_response(
    ai_provider,
    model: str,
    messages: list[ProviderChatMessage],
    payload: ChatCompletionRequest,
    request_id: str,
    provider_name: str,
    user: User | None,
    db: AsyncSession,
    usage_service: UsageService,
    cost_service: CostService,
    start_time: float,
) -> AsyncIterator[str]:
    chunk_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"

    try:
        async for chunk in ai_provider.stream_completion(
            model=model,
            messages=messages,
            temperature=payload.temperature,
            top_p=payload.top_p,
            max_tokens=payload.max_tokens,
            stop=payload.stop,
            tools=payload.tools,
            tool_choice=payload.tool_choice,
            response_format=payload.response_format,
        ):
            delta = chunk.delta
            finish = chunk.finish_reason

            chunk_data = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": delta,
                    "finish_reason": finish,
                }],
            }
            yield f"data: {json.dumps(chunk_data)}\n\n"

            if finish:
                break

        yield "data: [DONE]\n\n"

        latency = (time.time() - start_time) * 1000
        routing_engine.record_latency(model, latency)

        await usage_service.log_request(
            request_id=request_id,
            model=model,
            provider=provider_name,
            latency_ms=latency,
            status="success",
            user_id=user.id if user else None,
            organization_id=user.organization_id if user else None,
        )

    except Exception as e:
        latency = (time.time() - start_time) * 1000
        await usage_service.log_request(
            request_id=request_id,
            model=model,
            provider=provider_name,
            latency_ms=latency,
            status="error",
            error=str(e),
            user_id=user.id if user else None,
            organization_id=user.organization_id if user else None,
        )
        error_chunk = {
            "error": {
                "message": str(e),
                "type": "provider_error",
                "code": "PROVIDER_ERROR",
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"


@router.get("/v1/models", response_model=ModelListResponse)
async def list_models(
    db: AsyncSession = Depends(get_db),
    principal: tuple[User | None, APIKey | None] = Depends(get_api_key_or_user),
):
    result = await db.execute(select(Model).where(Model.is_enabled))
    models = result.scalars().all()

    return ModelListResponse(
        data=[
            ModelInfo(
                id=m.provider_model_id,
                created=int(m.created_at.timestamp()) if m.created_at else 0,
                owned_by=m.provider_id.hex[:8],
            )
            for m in models
        ]
    )
