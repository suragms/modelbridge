from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_api_key_or_user
from app.db.base import get_db
from app.models.api_key import APIKey
from app.models.model import Model
from app.models.request_log import (
    REQUEST_STATUS_COMPLETED,
    REQUEST_STATUS_FAILED,
    REQUEST_STATUS_PROCESSING,
    USAGE_SOURCE_ESTIMATED,
    USAGE_SOURCE_PROVIDER,
    USAGE_SOURCE_UNAVAILABLE,
)
from app.models.user import User
from app.observability.tracing import SpanKind, get_tracer
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
from app.services.metrics import record_request
from app.services.response_cache import (
    CachePolicy,
    build_chat_cache_key,
    get_response_cache,
    is_chat_cacheable,
    parse_cache_policy,
)
from app.services.routing import RouteService, RouteTarget
from app.services.capabilities import collect_image_urls, detect_chat_capabilities
from app.services.params import normalize_chat_params
from app.services.token_estimator import estimate_message_tokens
from app.services.tool_calls import normalize_message_tool_calls
from app.services.usage import UsageService, generate_request_id
from app.utils.image_urls import validate_request_image_urls

router = APIRouter(tags=["OpenAI-Compatible"])

routing_engine = RoutingEngine()
tracer = get_tracer()


def _required_capabilities(payload: ChatCompletionRequest) -> set[str]:
    return detect_chat_capabilities(
        payload.messages,
        payload.tools,
        payload.tool_choice,
        payload.response_format,
        payload.stream,
    )


def _is_retryable_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {429, 500, 502, 503, 504}
    if isinstance(exc, httpx.TransportError):
        return True
    message = str(exc).lower()
    if any(token in message for token in ("auth", "unauthorized", "api key", "invalid request")):
        return False
    return True


def _classify_error(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code == 401:
            return "AUTHENTICATION_ERROR", "AUTH_ERROR"
        if code == 429:
            return "RATE_LIMIT_ERROR", "RATE_LIMIT"
        if code in {400, 422}:
            return "VALIDATION_ERROR", "VALIDATION_ERROR"
        if code in {500, 502, 503, 504}:
            return "PROVIDER_ERROR", f"HTTP_{code}"
        return "PROVIDER_ERROR", f"HTTP_{code}"
    if isinstance(exc, httpx.TimeoutException):
        return "PROVIDER_TIMEOUT", "TIMEOUT"
    if isinstance(exc, httpx.TransportError):
        return "PROVIDER_ERROR", "TRANSPORT_ERROR"
    message = str(exc).lower()
    if "auth" in message or "unauthorized" in message:
        return "AUTHENTICATION_ERROR", "AUTH_ERROR"
    if "rate limit" in message:
        return "RATE_LIMIT_ERROR", "RATE_LIMIT"
    if "routing" in message:
        return "ROUTING_ERROR", "ROUTING_ERROR"
    return "PROVIDER_ERROR", "PROVIDER_ERROR"


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


def _auth_context(
    user: User | None, api_key: APIKey | None
) -> tuple[uuid.UUID | None, uuid.UUID | None, uuid.UUID | None]:
    if api_key:
        return api_key.user_id, api_key.id, api_key.organization_id
    if user:
        return user.id, None, user.organization_id
    return None, None, None


@router.post("/v1/chat/completions")
async def chat_completions(
    payload: ChatCompletionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    principal: tuple[User | None, APIKey | None] = Depends(get_api_key_or_user),
):
    user, authenticated_key = principal
    user_id, api_key_id, org_id = _auth_context(user, authenticated_key)

    from app.services.gateway_guard import enforce_gateway_guards

    rate_headers = await enforce_gateway_guards(
        request,
        db,
        user=user,
        api_key=authenticated_key,
        organization_id=org_id,
        path="/v1/chat/completions",
        messages=payload.messages,
    )
    request.state.rate_limit_headers = rate_headers

    cache_policy = parse_cache_policy(request.headers.get("X-ModelBridge-Cache-Policy"))

    if authenticated_key is not None:
        authenticated_key.last_used_at = datetime.now(UTC)

    request_id = generate_request_id()
    start_time = time.time()

    with tracer.start_span("incoming_request", SpanKind.SERVER) as span:
        span.set_attribute("request_id", request_id)
        span.set_attribute("model", payload.model)

    usage_service = UsageService(db)
    cost_service = CostService(db)

    with tracer.start_span("routing", SpanKind.INTERNAL):
        route_service = RouteService(db)
        policy = await route_service.get_active_policy(strategy=None)
        required_caps = _required_capabilities(payload)
        validate_request_image_urls(collect_image_urls(payload.messages))
        caps_str = ",".join(sorted(required_caps))
        plan = await route_service.plan(
            requested_model=payload.model,
            required_capabilities=required_caps,
            policy=policy,
            strategy=None,
            request_count=None,
            org_id=org_id,
        )

    if not plan.targets:
        await usage_service.complete_request(
            request_id=request_id,
            model=payload.model,
            provider="none",
            latency_ms=(time.time() - start_time) * 1000,
            status=REQUEST_STATUS_FAILED,
            error="No providers available",
            error_type="ROUTING_ERROR",
            error_code="NO_PROVIDERS",
            requested_model=payload.model,
            user_id=user_id,
            api_key_id=api_key_id,
            organization_id=org_id,
        )
        if payload.model == "auto":
            raise HTTPException(status_code=503, detail="No healthy providers available for auto routing")
        raise HTTPException(status_code=404, detail=f"Model '{payload.model}' not found or unavailable")

    cache = get_response_cache()
    cache_key: str | None = None
    if not payload.stream and is_chat_cacheable(
        stream=False,
        tools=payload.tools,
        tool_choice=payload.tool_choice,
        policy=cache_policy,
    ):
        cache_key = build_chat_cache_key(
            org_id=str(org_id) if org_id else None,
            model=payload.model,
            messages=payload.messages,
            temperature=payload.temperature,
            top_p=payload.top_p,
            max_tokens=payload.max_tokens,
            stop=payload.stop,
            response_format=payload.response_format,
        )
        if cache_policy == CachePolicy.FORCE_CACHE:
            cached = await cache.lookup(cache_key, endpoint="chat", policy=cache_policy)
            if cached is None:
                raise HTTPException(status_code=412, detail="Cache miss under FORCE_CACHE policy")
        else:
            cached = await cache.lookup(cache_key, endpoint="chat", policy=cache_policy)
            if cached is not None:
                return ChatCompletionResponse.model_validate(cached["response"])

    await usage_service.create_request(
        request_id=request_id,
        requested_model=plan.requested_model,
        user_id=user_id,
        api_key_id=api_key_id,
        organization_id=org_id,
        routing_policy=plan.policy_name,
        routing_strategy=plan.strategy,
        request_type="chat",
        required_capabilities=caps_str,
    )

    messages = _provider_messages(payload.messages)

    if payload.stream:
        return StreamingResponse(
            _stream_response(
                plan, messages, payload, request_id, user_id, api_key_id, org_id,
                db, usage_service, cost_service, start_time,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-Request-ID": request_id,
            },
        )

    return await _execute_non_streaming(
        plan, messages, payload, request_id, user_id, api_key_id, org_id,
        db, usage_service, cost_service, start_time,
        cache_key=cache_key,
        cache_policy=cache_policy,
    )


async def _execute_non_streaming(
    plan,
    messages: list[ProviderChatMessage],
    payload: ChatCompletionRequest,
    request_id: str,
    user_id: uuid.UUID | None,
    api_key_id: uuid.UUID | None,
    org_id: uuid.UUID | None,
    db: AsyncSession,
    usage_service: UsageService,
    cost_service: CostService,
    start_time: float,
    cache_key: str | None = None,
    cache_policy: CachePolicy = CachePolicy.DEFAULT,
) -> ChatCompletionResponse:
    registry = get_provider_registry()
    attempted: set[str] = set()
    fallback_count = 0

    await usage_service.update_status(request_id, REQUEST_STATUS_PROCESSING)

    for target in plan.targets:
        model_key = str(target.candidate.model.id)
        if model_key in attempted:
            continue
        attempted.add(model_key)

        provider_start = time.time()

        try:
            ai_provider = registry.create_provider(
                provider_type=target.provider.type,
                api_key=target.api_key,
                base_url=target.provider.base_url,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        norm = normalize_chat_params(target.provider.type, payload)

        try:
            with tracer.start_span("provider_request", SpanKind.CLIENT):
                result = await ai_provider.chat_completion(
                    model=target.resolved_model,
                    messages=messages,
                    **norm.as_kwargs(),
                )
        except Exception as e:
            error_type, error_code = _classify_error(e)
            if fallback_count > 0 and not _is_retryable_error(e):
                await _finalize_request(
                    usage_service, request_id, plan, target, start_time, provider_start,
                    user_id, api_key_id, org_id,
                    status=REQUEST_STATUS_FAILED, error=str(e),
                    error_type=error_type, error_code=error_code,
                    fallback_count=fallback_count,
                )
                raise HTTPException(status_code=getattr(e, "status_code", 502), detail=f"Provider error: {str(e)}")
            if not _is_retryable_error(e):
                await _finalize_request(
                    usage_service, request_id, plan, target, start_time, provider_start,
                    user_id, api_key_id, org_id,
                    status=REQUEST_STATUS_FAILED, error=str(e),
                    error_type=error_type, error_code=error_code,
                    fallback_count=fallback_count,
                )
                raise HTTPException(status_code=getattr(e, "status_code", 400), detail=f"Provider error: {str(e)}")
            fallback_count += 1
            continue

        latency = (time.time() - start_time) * 1000
        routing_engine.record_latency(str(target.candidate.model.id), latency)
        target.candidate.model.average_latency_ms = routing_engine.get_avg_latency(str(target.candidate.model.id))
        target.candidate.model.last_synced_at = datetime.now(UTC)

        await _finalize_request(
            usage_service, request_id, plan, target, start_time, provider_start,
            user_id, api_key_id, org_id,
            status=REQUEST_STATUS_COMPLETED, fallback_count=fallback_count,
        )

        usage_data = result.usage or {}
        prompt_tokens = usage_data.get("prompt_tokens", 0)
        completion_tokens = usage_data.get("completion_tokens", 0)
        usage_source = USAGE_SOURCE_PROVIDER if (prompt_tokens or completion_tokens) else USAGE_SOURCE_UNAVAILABLE

        if usage_source == USAGE_SOURCE_UNAVAILABLE:
            est_in, est_out = estimate_message_tokens(
                [{"content": m.content} for m in payload.messages]
            )
            prompt_tokens = est_in
            completion_tokens = est_out
            usage_source = USAGE_SOURCE_ESTIMATED

        await usage_service.log_usage(
            request_id=request_id,
            model=target.resolved_model,
            provider=target.provider.name,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            usage_source=usage_source,
            user_id=user_id,
            organization_id=org_id,
        )
        await cost_service.estimate_and_log(
            request_id=request_id,
            model_name=target.resolved_model,
            provider_name=target.provider.name,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            user_id=user_id,
            organization_id=org_id,
        )

        record_request(
            status=REQUEST_STATUS_COMPLETED,
            provider=target.provider.name,
            duration_seconds=latency / 1000,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
        )

        choices = []
        for choice_data in result.choices:
            msg = normalize_message_tool_calls(choice_data.get("message", {}))
            message = {"role": msg.get("role", "assistant"), "content": msg.get("content")}
            if msg.get("tool_calls"):
                message["tool_calls"] = msg["tool_calls"]
            choices.append(ChatChoice(
                index=choice_data.get("index", 0),
                message=message,
                finish_reason=choice_data.get("finish_reason", "stop"),
            ))

        response = ChatCompletionResponse(
            id=result.id,
            created=int(time.time()),
            model=target.resolved_model,
            choices=choices,
            usage=UsageInfo(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )

        if cache_key and is_chat_cacheable(
            stream=False,
            tools=payload.tools,
            tool_choice=payload.tool_choice,
            policy=cache_policy,
        ):
            cache = get_response_cache()
            await cache.store(
                cache_key,
                {
                    "response": response.model_dump(),
                    "request_id": request_id,
                    "provider": target.provider.name,
                    "model": target.resolved_model,
                },
                endpoint="chat",
                policy=cache_policy,
            )

        return response

    latency = (time.time() - start_time) * 1000
    await usage_service.complete_request(
        request_id=request_id,
        model=plan.requested_model,
        provider=plan.targets[0].provider.name if plan.targets else "unknown",
        latency_ms=latency,
        status=REQUEST_STATUS_FAILED,
        error="All providers failed",
        error_type="PROVIDER_ERROR",
        error_code="ALL_FAILED",
        routing_strategy=plan.strategy,
        fallback_used=fallback_count > 0,
        requested_model=plan.requested_model,
        routing_policy=plan.policy_name,
        candidates_count=len(plan.targets),
        fallback_count=fallback_count,
        user_id=user_id,
        api_key_id=api_key_id,
        organization_id=org_id,
    )
    record_request(
        status=REQUEST_STATUS_FAILED,
        provider=plan.targets[0].provider.name if plan.targets else "unknown",
        duration_seconds=latency / 1000,
        error_type="PROVIDER_ERROR",
    )
    raise HTTPException(status_code=502, detail="All providers failed")


async def _finalize_request(
    usage_service: UsageService,
    request_id: str,
    plan,
    target: RouteTarget,
    start_time: float,
    provider_start: float,
    user_id: uuid.UUID | None,
    api_key_id: uuid.UUID | None,
    org_id: uuid.UUID | None,
    status: str,
    error: str | None = None,
    error_type: str | None = None,
    error_code: str | None = None,
    fallback_count: int = 0,
) -> None:
    latency = (time.time() - start_time) * 1000
    provider_latency = (time.time() - provider_start) * 1000
    await usage_service.complete_request(
        request_id=request_id,
        model=target.resolved_model,
        provider=target.provider.name,
        latency_ms=latency,
        status=status,
        error=error,
        error_type=error_type,
        error_code=error_code,
        routing_strategy=plan.strategy,
        fallback_used=fallback_count > 0,
        requested_model=plan.requested_model,
        routing_policy=plan.policy_name,
        candidates_count=len(plan.targets),
        fallback_count=fallback_count,
        provider_latency_ms=provider_latency,
        user_id=user_id,
        api_key_id=api_key_id,
        organization_id=org_id,
    )


async def _stream_response(
    plan,
    messages: list[ProviderChatMessage],
    payload: ChatCompletionRequest,
    request_id: str,
    user_id: uuid.UUID | None,
    api_key_id: uuid.UUID | None,
    org_id: uuid.UUID | None,
    db: AsyncSession,
    usage_service: UsageService,
    cost_service: CostService,
    start_time: float,
) -> AsyncIterator[str]:
    registry = get_provider_registry()
    target = plan.targets[0]
    chunk_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    provider_start = time.time()

    await usage_service.update_status(request_id, REQUEST_STATUS_PROCESSING)

    ai_provider = registry.create_provider(
        provider_type=target.provider.type,
        api_key=target.api_key,
        base_url=target.provider.base_url,
    )

    stream_usage: dict | None = None
    output_text = ""

    try:
        with tracer.start_span("provider_stream", SpanKind.CLIENT):
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

                if delta.get("content"):
                    output_text += str(delta["content"])

                if hasattr(chunk, "usage") and chunk.usage:
                    stream_usage = chunk.usage

                chunk_data = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": target.resolved_model,
                    "modelbridge": {
                        "model": target.resolved_model,
                        "provider": target.provider.name,
                        "strategy": plan.strategy,
                        "request_id": request_id,
                    },
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

        await _finalize_request(
            usage_service, request_id, plan, target, start_time, provider_start,
            user_id, api_key_id, org_id,
            status=REQUEST_STATUS_COMPLETED,
        )

        prompt_tokens = 0
        completion_tokens = 0
        usage_source = USAGE_SOURCE_UNAVAILABLE

        if stream_usage:
            prompt_tokens = stream_usage.get("prompt_tokens", 0)
            completion_tokens = stream_usage.get("completion_tokens", 0)
            usage_source = USAGE_SOURCE_PROVIDER
        else:
            est_in, _ = estimate_message_tokens(
                [{"content": m.content} for m in payload.messages]
            )
            prompt_tokens = est_in
            completion_tokens = max(1, len(output_text) // 4) if output_text else 0
            usage_source = USAGE_SOURCE_ESTIMATED

        await usage_service.log_usage(
            request_id=request_id,
            model=target.resolved_model,
            provider=target.provider.name,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            usage_source=usage_source,
            user_id=user_id,
            organization_id=org_id,
        )
        await cost_service.estimate_and_log(
            request_id=request_id,
            model_name=target.resolved_model,
            provider_name=target.provider.name,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            user_id=user_id,
            organization_id=org_id,
        )

        record_request(
            status=REQUEST_STATUS_COMPLETED,
            provider=target.provider.name,
            duration_seconds=latency / 1000,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
        )

    except Exception as e:
        latency = (time.time() - start_time) * 1000
        error_type, error_code = _classify_error(e)
        await _finalize_request(
            usage_service, request_id, plan, target, start_time, provider_start,
            user_id, api_key_id, org_id,
            status=REQUEST_STATUS_FAILED, error=str(e),
            error_type=error_type, error_code=error_code,
        )
        record_request(
            status=REQUEST_STATUS_FAILED,
            provider=target.provider.name,
            duration_seconds=latency / 1000,
            error_type=error_type,
        )
        error_chunk = {
            "error": {
                "message": str(e),
                "type": error_type.lower(),
                "code": error_code,
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
