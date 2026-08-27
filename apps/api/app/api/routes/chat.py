from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_api_key_or_user
from app.db.base import get_db
from app.models.api_key import APIKey
from app.models.model import Model
from app.models.provider import Provider
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
from app.services.routing import RouteService, RouteTarget
from app.services.usage import UsageService

router = APIRouter(tags=["OpenAI-Compatible"])

routing_engine = RoutingEngine()


# ---- capability detection & error classification -----------------------------

def _required_capabilities(payload: ChatCompletionRequest) -> set[str]:
    caps = {"chat"}
    if payload.tools:
        caps.add("tools")
    rf = payload.response_format or {}
    if rf.get("type") == "json_object" or rf.get("json_schema"):
        caps.add("json_mode")
    return caps


def _is_retryable_error(exc: Exception) -> bool:
    """Decide whether a provider failure warrants trying a fallback model.

    Network/timeout and server-side / rate-limit errors are retryable.
    Invalid requests, bad auth, unsupported params, and malformed messages are
    NOT retryable (per the Phase 2 spec).
    """
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {429, 500, 502, 503, 504}
    if isinstance(exc, httpx.TransportError):
        return True
    # Generic provider errors are treated as retryable only if they look like
    # upstream failures; anything else is surfaced immediately.
    message = str(exc).lower()
    if any(token in message for token in ("auth", "unauthorized", "api key", "invalid request")):
        return False
    return True


# ---- provider message conversion ---------------------------------------------

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


# ---- OpenAI-compatible chat completions --------------------------------------

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

    route_service = RouteService(db)
    policy = await route_service.get_active_policy(strategy=None)
    plan = await route_service.plan(
        requested_model=payload.model,
        required_capabilities=_required_capabilities(payload),
        policy=policy,
        strategy=None,
        request_count=None,
        org_id=user.organization_id if user else None,
    )

    if not plan.targets:
        if payload.model == "auto":
            raise HTTPException(status_code=503, detail="No healthy providers available for auto routing")
        raise HTTPException(status_code=404, detail=f"Model '{payload.model}' not found or unavailable")

    usage_service = UsageService(db)
    cost_service = CostService(db)
    messages = _provider_messages(payload.messages)

    if payload.stream:
        return StreamingResponse(
            _stream_response(
                plan, messages, payload, request_id, user, db, usage_service, cost_service, start_time,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming: execute with automatic fallback.
    return await _execute_non_streaming(
        plan, messages, payload, request_id, user, db, usage_service, cost_service, start_time,
    )


async def _execute_non_streaming(
    plan,
    messages: list[ProviderChatMessage],
    payload: ChatCompletionRequest,
    request_id: str,
    user: User | None,
    db: AsyncSession,
    usage_service: UsageService,
    cost_service: CostService,
    start_time: float,
) -> ChatCompletionResponse:
    registry = get_provider_registry()
    attempted: set[str] = set()
    fallback_count = 0

    for target in plan.targets:
        model_key = str(target.candidate.model.id)
        if model_key in attempted:
            continue  # prevent infinite fallback loops
        attempted.add(model_key)

        try:
            ai_provider = registry.create_provider(
                provider_type=target.provider.type,
                api_key=target.api_key,
                base_url=target.provider.base_url,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        try:
            result = await ai_provider.chat_completion(
                model=target.resolved_model,
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
            if fallback_count > 0 and not _is_retryable_error(e):
                # A later provider failed with a non-retryable error: surface it.
                await _log_decision(
                    usage_service, request_id, plan, target, start_time,
                    user, status="error", error=str(e), fallback_count=fallback_count,
                )
                raise HTTPException(status_code=getattr(e, "status_code", 502), detail=f"Provider error: {str(e)}")
            if not _is_retryable_error(e):
                await _log_decision(
                    usage_service, request_id, plan, target, start_time,
                    user, status="error", error=str(e), fallback_count=fallback_count,
                )
                raise HTTPException(status_code=getattr(e, "status_code", 400), detail=f"Provider error: {str(e)}")
            # Retryable: try the next target.
            fallback_count += 1
            continue

        # Success.
        latency = (time.time() - start_time) * 1000
        routing_engine.record_latency(str(target.candidate.model.id), latency)
        target.candidate.model.average_latency_ms = routing_engine.get_avg_latency(str(target.candidate.model.id))
        target.candidate.model.last_synced_at = datetime.now(UTC)

        await _log_decision(
            usage_service, request_id, plan, target, start_time,
            user, status="success", fallback_count=fallback_count,
        )
        usage_data = result.usage
        await usage_service.log_usage(
            request_id=request_id,
            model=target.resolved_model,
            provider=target.provider.name,
            input_tokens=usage_data.get("prompt_tokens", 0),
            output_tokens=usage_data.get("completion_tokens", 0),
            user_id=user.id if user else None,
            organization_id=user.organization_id if user else None,
        )
        await cost_service.estimate_and_log(
            request_id=request_id,
            model_name=target.resolved_model,
            provider_name=target.provider.name,
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
            model=target.resolved_model,
            choices=choices,
            usage=UsageInfo(**usage_data),
        )

    # All retryable attempts exhausted.
    latency = (time.time() - start_time) * 1000
    await usage_service.log_request(
        request_id=request_id,
        model=plan.requested_model,
        provider=plan.targets[0].provider.name if plan.targets else "unknown",
        latency_ms=latency,
        status="error",
        error="All providers failed",
        routing_strategy=plan.strategy,
        fallback_used=fallback_count > 0,
        requested_model=plan.requested_model,
        routing_policy=plan.policy_name,
        candidates_count=len(plan.targets),
        fallback_count=fallback_count,
        user_id=user.id if user else None,
        organization_id=user.organization_id if user else None,
    )
    raise HTTPException(status_code=502, detail="All providers failed")


async def _log_decision(
    usage_service: UsageService,
    request_id: str,
    plan,
    target: RouteTarget,
    start_time: float,
    user: User | None,
    status: str,
    error: str | None = None,
    fallback_count: int = 0,
) -> None:
    latency = (time.time() - start_time) * 1000
    await usage_service.log_request(
            request_id=request_id,
            model=target.resolved_model,
            provider=target.provider.name,
            latency_ms=latency,
            status=status,
            error=error,
            routing_strategy=plan.strategy,
            fallback_used=fallback_count > 0,
            requested_model=plan.requested_model,
            routing_policy=plan.policy_name,
            candidates_count=len(plan.targets),
            fallback_count=fallback_count,
            user_id=user.id if user else None,
            organization_id=user.organization_id if user else None,
        )


async def _stream_response(
    plan,
    messages: list[ProviderChatMessage],
    payload: ChatCompletionRequest,
    request_id: str,
    user: User | None,
    db: AsyncSession,
    usage_service: UsageService,
    cost_service: CostService,
    start_time: float,
) -> AsyncIterator[str]:
    registry = get_provider_registry()
    target = plan.targets[0]
    chunk_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"

    # Routing is completed *before* streaming begins, so no fallback switches
    # happen once a response is streaming (documented Phase 2 decision).
    ai_provider = registry.create_provider(
        provider_type=target.provider.type,
        api_key=target.api_key,
        base_url=target.provider.base_url,
    )

    try:
        async for chunk in ai_provider.stream_completion(
            model=target.resolved_model,
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
                "model": target.resolved_model,
                "modelbridge": {"model": target.resolved_model, "provider": target.provider.name, "strategy": plan.strategy},
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
        routing_engine.record_latency(str(target.candidate.model.id), latency)
        target.candidate.model.average_latency_ms = routing_engine.get_avg_latency(str(target.candidate.model.id))

        await usage_service.log_request(
            request_id=request_id,
            model=target.resolved_model,
            provider=target.provider.name,
            latency_ms=latency,
            status="success",
            routing_strategy=plan.strategy,
            fallback_used=False,
            requested_model=plan.requested_model,
            routing_policy=plan.policy_name,
            candidates_count=len(plan.targets),
            fallback_count=0,
            user_id=user.id if user else None,
            organization_id=user.organization_id if user else None,
        )

    except Exception as e:
        latency = (time.time() - start_time) * 1000
        await usage_service.log_request(
            request_id=request_id,
            model=target.resolved_model,
            provider=target.provider.name,
            latency_ms=latency,
            status="error",
            error=str(e),
            routing_strategy=plan.strategy,
            fallback_used=False,
            requested_model=plan.requested_model,
            routing_policy=plan.policy_name,
            candidates_count=len(plan.targets),
            fallback_count=0,
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
    result = await db.execute(select(Model).where(Model.is_enabled).order_by(Model.display_name))
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
