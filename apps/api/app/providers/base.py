from __future__ import annotations

import abc
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class ProviderModel:
    id: str
    name: str
    context_window: int = 4096
    input_price_per_1k: float = 0.0
    output_price_per_1k: float = 0.0
    supports_streaming: bool = True
    supports_tools: bool = False
    supports_embeddings: bool = False
    supports_vision: bool = False
    supports_json_mode: bool = False
    quality_score: float = 0.5


@dataclass
class ChatMessage:
    role: str
    content: str | list | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict] | None = None


@dataclass
class ChatCompletionResult:
    id: str
    model: str
    choices: list[dict]
    usage: dict
    finish_reason: str = "stop"


@dataclass
class StreamChunk:
    id: str
    model: str
    delta: dict
    finish_reason: str | None = None


@dataclass
class EmbeddingResult:
    embeddings: list[list[float]]
    model: str
    usage: dict


class AIProvider(abc.ABC):
    """Base interface for all AI providers."""

    provider_type: str = "base"

    def __init__(self, api_key: str | None = None, base_url: str | None = None, **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.config = kwargs

    @abc.abstractmethod
    async def chat_completion(
        self,
        model: str,
        messages: list[ChatMessage],
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
        stop: str | list[str] | None = None,
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
        response_format: dict | None = None,
        **kwargs,
    ) -> ChatCompletionResult:
        ...

    @abc.abstractmethod
    async def stream_completion(
        self,
        model: str,
        messages: list[ChatMessage],
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
        stop: str | list[str] | None = None,
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
        response_format: dict | None = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        ...

    @abc.abstractmethod
    async def list_models(self) -> list[ProviderModel]:
        ...

    @abc.abstractmethod
    async def health_check(self) -> bool:
        ...

    async def generate_embeddings(
        self,
        model: str,
        input_text: str | list[str],
    ) -> EmbeddingResult:
        raise NotImplementedError(f"{self.provider_type} does not support embeddings")
