from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.chat import ChatCompletionRequest, ChatCompletionResponse, ChatMessage


class PlaygroundChatRequest(BaseModel):
    """Dashboard playground request — uses the same gateway as /v1/chat/completions."""

    model: str = "auto"
    messages: list[ChatMessage]
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    stream: bool = False
    stop: str | list[str] | None = None
    tools: list[dict] | None = None
    tool_choice: str | dict | None = None
    response_format: dict | None = None


class PlaygroundRoutingInfo(BaseModel):
    requested_model: str
    selected_model: str
    provider: str
    strategy: str
    routing_policy: str | None = None
    required_capabilities: list[str] = Field(default_factory=list)


class PlaygroundChatResponse(BaseModel):
    request_id: str
    response: ChatCompletionResponse
    routing: PlaygroundRoutingInfo
    latency_ms: float
    estimated_total_cost: float | None = None
    usage_source: str | None = None


class PlaygroundCompareRequest(BaseModel):
    model_a: str
    model_b: str
    messages: list[ChatMessage]
    temperature: float | None = None
    max_tokens: int | None = None
    tools: list[dict] | None = None
    tool_choice: str | dict | None = None
    response_format: dict | None = None


class PlaygroundCompareSide(BaseModel):
    model: str
    provider: str | None = None
    request_id: str | None = None
    success: bool
    response: ChatCompletionResponse | None = None
    error: str | None = None
    latency_ms: float | None = None
    total_tokens: int | None = None
    estimated_total_cost: float | None = None


class PlaygroundCompareResponse(BaseModel):
    side_a: PlaygroundCompareSide
    side_b: PlaygroundCompareSide
