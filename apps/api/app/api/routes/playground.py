from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.schemas.chat import ChatCompletionRequest
from app.schemas.playground import (
    PlaygroundChatRequest,
    PlaygroundChatResponse,
    PlaygroundCompareRequest,
    PlaygroundCompareResponse,
    PlaygroundCompareSide,
    PlaygroundRoutingInfo,
)
from app.services.gateway import execute_chat

router = APIRouter(prefix="/playground", tags=["Playground"])


def _to_chat_request(payload: PlaygroundChatRequest) -> ChatCompletionRequest:
    return ChatCompletionRequest(
        model=payload.model,
        messages=payload.messages,
        temperature=payload.temperature,
        top_p=payload.top_p,
        max_tokens=payload.max_tokens,
        stream=False,
        stop=payload.stop,
        tools=payload.tools,
        tool_choice=payload.tool_choice,
        response_format=payload.response_format,
    )


@router.post("/chat", response_model=PlaygroundChatResponse)
async def playground_chat(
    payload: PlaygroundChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.stream:
        raise HTTPException(status_code=400, detail="Use /v1/chat/completions for streaming")

    result = await execute_chat(_to_chat_request(payload), db, user, None)
    return PlaygroundChatResponse(
        request_id=result.request_id,
        response=result.response,
        routing=PlaygroundRoutingInfo(
            requested_model=payload.model,
            selected_model=result.selected_model,
            provider=result.provider,
            strategy=result.strategy,
            routing_policy=result.routing_policy,
            required_capabilities=result.required_capabilities,
        ),
        latency_ms=result.latency_ms,
        estimated_total_cost=result.estimated_total_cost,
        usage_source=result.usage_source,
    )


@router.post("/compare", response_model=PlaygroundCompareResponse)
async def playground_compare(
    payload: PlaygroundCompareRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    async def run_side(model: str) -> PlaygroundCompareSide:
        start = time.time()
        req = ChatCompletionRequest(
            model=model,
            messages=payload.messages,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            tools=payload.tools,
            tool_choice=payload.tool_choice,
            response_format=payload.response_format,
            stream=False,
        )
        try:
            result = await execute_chat(req, db, user, None)
            return PlaygroundCompareSide(
                model=result.selected_model,
                provider=result.provider,
                request_id=result.request_id,
                success=True,
                response=result.response,
                latency_ms=result.latency_ms,
                total_tokens=result.response.usage.total_tokens,
                estimated_total_cost=result.estimated_total_cost,
            )
        except HTTPException as e:
            return PlaygroundCompareSide(
                model=model,
                success=False,
                error=str(e.detail),
                latency_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return PlaygroundCompareSide(
                model=model,
                success=False,
                error=str(e),
                latency_ms=(time.time() - start) * 1000,
            )

    side_a = await run_side(payload.model_a)
    side_b = await run_side(payload.model_b)
    return PlaygroundCompareResponse(side_a=side_a, side_b=side_b)
