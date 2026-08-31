"""Shared gateway execution helpers for chat, embeddings, and playground."""

from __future__ import annotations

import time

from dataclasses import dataclass

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey
from app.models.request_log import (
    REQUEST_STATUS_COMPLETED,
    REQUEST_STATUS_FAILED,
    REQUEST_STATUS_PROCESSING,
    USAGE_SOURCE_ESTIMATED,
    USAGE_SOURCE_PROVIDER,
    USAGE_SOURCE_UNAVAILABLE,
)
from app.models.user import User
from app.providers.base import ChatMessage as ProviderChatMessage
from app.providers.registry import get_provider_registry
from app.router.engine import RoutingEngine
from app.schemas.chat import (
    ChatChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    EmbeddingRequest,
    EmbeddingData,
    EmbeddingResponse,
    UsageInfo,
)
from app.services.capabilities import (
    collect_image_urls,
    detect_chat_capabilities,
    raise_no_compatible_model,
)
from app.services.cost import CostService
from app.models.cloud import UsageEventType
from app.services.cloud.metering import MeteringService
from app.services.cloud.quotas import QuotaExceeded, QuotaService
from app.models.cloud import QuotaResource
from app.services.params import normalize_chat_params
from app.services.response_cache import (
    CachePolicy,
    build_chat_cache_key,
    build_embedding_cache_key,
    get_response_cache,
    is_chat_cacheable,
    is_embedding_cacheable,
    parse_cache_policy,
)
from app.services.governance.pipeline import (
    evaluate_pre_request,
    evaluate_response,
    extract_text,
    filter_targets,
    redact_messages,
)
from app.services.routing import RouteService, RouteTarget
from app.services.token_estimator import estimate_message_tokens
from app.services.tool_calls import normalize_message_tool_calls
from app.services.usage import UsageService, generate_request_id
from app.utils.image_urls import validate_request_image_urls

routing_engine = RoutingEngine()


@dataclass
class GatewayResult:
    response: ChatCompletionResponse
    request_id: str
    provider: str
    selected_model: str
    strategy: str
    routing_policy: str | None
    required_capabilities: list[str]
    latency_ms: float
    estimated_total_cost: float | None = None
    usage_source: str | None = None


def auth_context(
    user: User | None, api_key: APIKey | None
) -> tuple:
    if api_key:
        return api_key.user_id, api_key.id, api_key.organization_id
    if user:
        return user.id, None, user.organization_id
    return None, None, None


def is_retryable_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {429, 500, 502, 503, 504}
    if isinstance(exc, httpx.TransportError):
        return True
    message = str(exc).lower()
    if any(token in message for token in ("auth", "unauthorized", "api key", "invalid request")):
        return False
    return True


def classify_error(exc: Exception) -> tuple[str, str]:
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
    return "PROVIDER_ERROR", "PROVIDER_ERROR"


def provider_messages(messages: list) -> list[ProviderChatMessage]:
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


async def finalize_request(
    usage_service: UsageService,
    request_id: str,
    plan,
    target: RouteTarget,
    start_time: float,
    provider_start: float,
    user_id,
    api_key_id,
    org_id,
    status: str,
    request_type: str = "chat",
    required_capabilities: str | None = None,
    input_count: int | None = None,
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
        request_type=request_type,
        required_capabilities=required_capabilities,
        input_count=input_count,
    )


async def execute_chat(
    payload: ChatCompletionRequest,
    db: AsyncSession,
    user: User | None,
    api_key: APIKey | None,
    cache_policy: CachePolicy | str | None = None,
    approval_id: str | None = None,
) -> GatewayResult:
    user_id, api_key_id, org_id = auth_context(user, api_key)
    request_id = generate_request_id()
    start_time = time.time()
    policy = cache_policy if isinstance(cache_policy, CachePolicy) else parse_cache_policy(cache_policy)

    if org_id:
        quota_status = await QuotaService(db).check(org_id, QuotaResource.REQUESTS, increment=1)
        if not quota_status["allowed"]:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "QUOTA_EXCEEDED",
                    "message": f"Request quota exceeded ({quota_status['current']}/{quota_status['limit']})",
                    "type": "quota_error",
                },
            )

    required = detect_chat_capabilities(
        payload.messages,
        payload.tools,
        payload.tool_choice,
        payload.response_format,
        payload.stream,
    )
    validate_request_image_urls(collect_image_urls(payload.messages))
    caps_str = ",".join(sorted(required))

    gov = await evaluate_pre_request(
        db,
        org_id=org_id,
        user=user,
        api_key=api_key,
        requested_model=payload.model,
        messages=payload.messages,
        capabilities=required,
        request_type="chat",
        endpoint="/v1/chat/completions",
        request_id=request_id,
        approval_id=approval_id,
        expose_details=user is not None,
    )
    provider_messages_list = payload.messages
    if gov.should_redact_prompt:
        provider_messages_list = redact_messages(
            payload.messages, gov.redacted_text, extract_text(payload.messages)
        )

    route_service = RouteService(db)
    routing_policy = await route_service.get_active_policy(strategy=None)
    plan = await route_service.plan(
        requested_model=payload.model,
        required_capabilities=required,
        policy=routing_policy,
        strategy=None,
        request_count=None,
        org_id=org_id,
        restrictions=gov.restrictions,
    )
    plan.targets = filter_targets(plan.targets, gov.restrictions)

    if not plan.targets:
        raise_no_compatible_model(required, payload.model)

    usage_service = UsageService(db)
    cost_service = CostService(db)

    cache = get_response_cache()
    cache_key: str | None = None
    if is_chat_cacheable(
        stream=payload.stream,
        tools=payload.tools,
        tool_choice=payload.tool_choice,
        policy=policy,
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
            policy_fingerprint=gov.policy_fingerprint,
        )
        if policy == CachePolicy.FORCE_CACHE:
            cached = await cache.lookup(cache_key, endpoint="chat", policy=policy)
            if cached is None:
                raise HTTPException(status_code=412, detail="Cache miss under FORCE_CACHE policy")
        else:
            cached = await cache.lookup(cache_key, endpoint="chat", policy=policy)
            if cached is not None:
                response = ChatCompletionResponse.model_validate(cached["response"])
                return GatewayResult(
                    response=response,
                    request_id=cached.get("request_id", request_id),
                    provider=cached.get("provider", "cache"),
                    selected_model=cached.get("model", response.model),
                    strategy=plan.strategy,
                    routing_policy=plan.policy_name,
                    required_capabilities=sorted(required),
                    latency_ms=(time.time() - start_time) * 1000,
                )

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

    messages = provider_messages(provider_messages_list)
    response = await _execute_non_streaming(
        plan, messages, payload, request_id, user_id, api_key_id, org_id,
        usage_service, cost_service, start_time, required, caps_str,
    )

    # Response governance
    for choice in response.choices:
        if choice.message and isinstance(choice.message.content, str):
            choice.message.content = await evaluate_response(
                db,
                org_id=org_id,
                text=choice.message.content,
                ctx=gov,
                request_id=request_id,
                requested_model=payload.model,
                actor_id=user_id,
            )

    if cache_key and is_chat_cacheable(
        stream=False,
        tools=payload.tools,
        tool_choice=payload.tool_choice,
        policy=policy,
    ):
        target = plan.targets[0]
        await cache.store(
            cache_key,
            {
                "response": response.model_dump(),
                "request_id": request_id,
                "provider": target.provider.name,
                "model": target.resolved_model,
            },
            endpoint="chat",
            policy=policy,
        )

    latency = (time.time() - start_time) * 1000
    target = plan.targets[0]
    cost_rec = await usage_service.get_cost_for_request(request_id)
    usage_rec = await usage_service.get_usage_for_request(request_id)
    return GatewayResult(
        response=response,
        request_id=request_id,
        provider=target.provider.name,
        selected_model=target.resolved_model,
        strategy=plan.strategy,
        routing_policy=plan.policy_name,
        required_capabilities=sorted(required),
        latency_ms=latency,
        estimated_total_cost=cost_rec.total_cost if cost_rec else None,
        usage_source=usage_rec.usage_source if usage_rec else None,
    )


async def _execute_non_streaming(
    plan,
    messages: list[ProviderChatMessage],
    payload: ChatCompletionRequest,
    request_id: str,
    user_id,
    api_key_id,
    org_id,
    usage_service: UsageService,
    cost_service: CostService,
    start_time: float,
    required: set[str],
    caps_str: str,
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
            result = await ai_provider.chat_completion(
                model=target.resolved_model,
                messages=messages,
                **norm.as_kwargs(),
            )
        except Exception as e:
            error_type, error_code = classify_error(e)
            if fallback_count > 0 and not is_retryable_error(e):
                await finalize_request(
                    usage_service, request_id, plan, target, start_time, provider_start,
                    user_id, api_key_id, org_id, REQUEST_STATUS_FAILED,
                    request_type="chat", required_capabilities=caps_str,
                    error=str(e), error_type=error_type, error_code=error_code,
                    fallback_count=fallback_count,
                )
                raise HTTPException(status_code=getattr(e, "status_code", 502), detail=f"Provider error: {str(e)}")
            if not is_retryable_error(e):
                await finalize_request(
                    usage_service, request_id, plan, target, start_time, provider_start,
                    user_id, api_key_id, org_id, REQUEST_STATUS_FAILED,
                    request_type="chat", required_capabilities=caps_str,
                    error=str(e), error_type=error_type, error_code=error_code,
                    fallback_count=fallback_count,
                )
                raise HTTPException(status_code=getattr(e, "status_code", 400), detail=f"Provider error: {str(e)}")
            fallback_count += 1
            continue

        latency = (time.time() - start_time) * 1000
        routing_engine.record_latency(str(target.candidate.model.id), latency)

        await finalize_request(
            usage_service, request_id, plan, target, start_time, provider_start,
            user_id, api_key_id, org_id, REQUEST_STATUS_COMPLETED,
            request_type="chat", required_capabilities=caps_str,
            fallback_count=fallback_count,
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
        if org_id:
            metering = MeteringService(db)
            await metering.record(
                organization_id=org_id,
                event_type=UsageEventType.REQUEST,
                metadata={"provider": target.provider.name, "model": target.resolved_model, "status": "completed"},
            )
            total_tokens = prompt_tokens + completion_tokens
            if total_tokens:
                await metering.record(
                    organization_id=org_id,
                    event_type=UsageEventType.TOKENS,
                    quantity=float(total_tokens),
                    metadata={"provider": target.provider.name, "model": target.resolved_model},
                )

        choices = []
        for choice_data in result.choices:
            msg = normalize_message_tool_calls(choice_data.get("message", {}))
            content = msg.get("content")
            message = ChatMessage(role=msg.get("role", "assistant"), content=content)
            if msg.get("tool_calls"):
                message.tool_calls = msg["tool_calls"]
            choices.append(ChatChoice(
                index=choice_data.get("index", 0),
                message=message,
                finish_reason=choice_data.get("finish_reason", "stop"),
            ))

        return ChatCompletionResponse(
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

    raise_no_compatible_model(required, plan.requested_model)
    raise HTTPException(status_code=502, detail="All providers failed")  # pragma: no cover


async def execute_embeddings(
    payload: EmbeddingRequest,
    db: AsyncSession,
    user: User | None,
    api_key: APIKey | None,
    cache_policy: CachePolicy | str | None = None,
    approval_id: str | None = None,
) -> EmbeddingResponse:
    user_id, api_key_id, org_id = auth_context(user, api_key)
    request_id = generate_request_id()
    start_time = time.time()
    policy = cache_policy if isinstance(cache_policy, CachePolicy) else parse_cache_policy(cache_policy)

    if org_id:
        quota_status = await QuotaService(db).check(org_id, QuotaResource.REQUESTS, increment=1)
        if not quota_status["allowed"]:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "QUOTA_EXCEEDED",
                    "message": f"Request quota exceeded ({quota_status['current']}/{quota_status['limit']})",
                    "type": "quota_error",
                },
            )

    required = {"embeddings"}
    caps_str = "embeddings"

    inputs = payload.input if isinstance(payload.input, list) else [payload.input]
    if not inputs:
        raise HTTPException(status_code=400, detail="At least one input is required")

    gov = await evaluate_pre_request(
        db,
        org_id=org_id,
        user=user,
        api_key=api_key,
        requested_model=payload.model,
        messages=None,
        extra_text="\n".join(str(i) for i in inputs),
        capabilities=required,
        request_type="embedding",
        endpoint="/v1/embeddings",
        request_id=request_id,
        approval_id=approval_id,
        expose_details=user is not None,
    )

    cache = get_response_cache()
    cache_key: str | None = None
    if is_embedding_cacheable(policy=policy):
        cache_key = build_embedding_cache_key(
            org_id=str(org_id) if org_id else None,
            model=payload.model,
            inputs=[str(i) for i in inputs],
            encoding_format=payload.encoding_format,
            policy_fingerprint=gov.policy_fingerprint,
        )
        if policy == CachePolicy.FORCE_CACHE:
            cached = await cache.lookup(cache_key, endpoint="embeddings", policy=policy)
            if cached is None:
                raise HTTPException(status_code=412, detail="Cache miss under FORCE_CACHE policy")
        else:
            cached = await cache.lookup(cache_key, endpoint="embeddings", policy=policy)
            if cached is not None:
                return EmbeddingResponse.model_validate(cached["response"])

    route_service = RouteService(db)
    routing_policy = await route_service.get_active_policy(strategy=None)
    plan = await route_service.plan(
        requested_model=payload.model,
        required_capabilities=required,
        policy=routing_policy,
        strategy=None,
        org_id=org_id,
        restrictions=gov.restrictions,
    )
    plan.targets = filter_targets(plan.targets, gov.restrictions)
    if not plan.targets:
        raise_no_compatible_model(required, payload.model)

    usage_service = UsageService(db)
    cost_service = CostService(db)
    await usage_service.create_request(
        request_id=request_id,
        requested_model=plan.requested_model,
        user_id=user_id,
        api_key_id=api_key_id,
        organization_id=org_id,
        routing_policy=plan.policy_name,
        routing_strategy=plan.strategy,
        request_type="embedding",
        required_capabilities=caps_str,
        input_count=len(inputs),
    )

    registry = get_provider_registry()
    target = plan.targets[0]
    provider_start = time.time()

    try:
        ai_provider = registry.create_provider(
            provider_type=target.provider.type,
            api_key=target.api_key,
            base_url=target.provider.base_url,
        )
        result = await ai_provider.generate_embeddings(target.resolved_model, inputs)
    except NotImplementedError as e:
        raise HTTPException(
            status_code=400,
            detail={"code": "EMBEDDINGS_NOT_SUPPORTED", "message": str(e), "type": "capability_error"},
        ) from e
    except Exception as e:
        error_type, error_code = classify_error(e)
        await finalize_request(
            usage_service, request_id, plan, target, start_time, provider_start,
            user_id, api_key_id, org_id, REQUEST_STATUS_FAILED,
            request_type="embedding", required_capabilities=caps_str,
            input_count=len(inputs), error=str(e), error_type=error_type, error_code=error_code,
        )
        raise HTTPException(status_code=502, detail=f"Provider error: {str(e)}") from e

    latency = (time.time() - start_time) * 1000
    await finalize_request(
        usage_service, request_id, plan, target, start_time, provider_start,
        user_id, api_key_id, org_id, REQUEST_STATUS_COMPLETED,
        request_type="embedding", required_capabilities=caps_str, input_count=len(inputs),
    )

    usage_data = result.usage or {}
    prompt_tokens = usage_data.get("prompt_tokens", usage_data.get("total_tokens", 0))
    usage_source = USAGE_SOURCE_PROVIDER if prompt_tokens else USAGE_SOURCE_ESTIMATED
    if usage_source == USAGE_SOURCE_ESTIMATED:
        prompt_tokens = sum(max(1, len(str(t)) // 4) for t in inputs)

    await usage_service.log_usage(
        request_id=request_id,
        model=target.resolved_model,
        provider=target.provider.name,
        input_tokens=prompt_tokens,
        output_tokens=0,
        usage_source=usage_source,
        user_id=user_id,
        organization_id=org_id,
    )
    await cost_service.estimate_and_log(
        request_id=request_id,
        model_name=target.resolved_model,
        provider_name=target.provider.name,
        input_tokens=prompt_tokens,
        output_tokens=0,
        user_id=user_id,
        organization_id=org_id,
    )
    record_request(
        status=REQUEST_STATUS_COMPLETED,
        provider=target.provider.name,
        duration_seconds=latency / 1000,
        input_tokens=prompt_tokens,
    )
    if org_id:
        metering = MeteringService(db)
        await metering.record(
            organization_id=org_id,
            event_type=UsageEventType.REQUEST,
            metadata={"provider": target.provider.name, "model": target.resolved_model, "endpoint": "embeddings"},
        )
        if prompt_tokens:
            await metering.record(
                organization_id=org_id,
                event_type=UsageEventType.TOKENS,
                quantity=float(prompt_tokens),
                metadata={"provider": target.provider.name, "model": target.resolved_model},
            )

    response = EmbeddingResponse(
        data=[
            EmbeddingData(embedding=emb, index=i)
            for i, emb in enumerate(result.embeddings)
        ],
        model=result.model,
        usage=UsageInfo(
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            total_tokens=prompt_tokens,
        ),
    )

    if cache_key and is_embedding_cacheable(policy=policy):
        await cache.store(
            cache_key,
            {"response": response.model_dump()},
            endpoint="embeddings",
            policy=policy,
        )

    return response
