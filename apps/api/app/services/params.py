"""Request parameter normalization per provider type.

Unsupported parameters are dropped only when they are optional extras.
Required capability parameters (tools, response_format, vision content) are
never silently discarded — routing filters incompatible models instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Parameters the gateway forwards when the provider adapter understands them.
_COMMON = ("temperature", "top_p", "max_tokens", "stop", "stream")
_OPENAI_COMPAT = _COMMON + ("tools", "tool_choice", "response_format")

SUPPORTED_PARAMS: dict[str, frozenset[str]] = {
    "openai": frozenset(_OPENAI_COMPAT),
    "groq": frozenset(_OPENAI_COMPAT),
    "openrouter": frozenset(_OPENAI_COMPAT),
    "lmstudio": frozenset(_OPENAI_COMPAT),
    "custom": frozenset(_OPENAI_COMPAT),
    "ollama": frozenset(_COMMON + ("tools", "response_format")),
    "anthropic": frozenset(_COMMON + ("tools", "tool_choice")),
    "gemini": frozenset(_COMMON + ("tools", "response_format")),
}


@dataclass
class NormalizedParams:
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    stop: str | list[str] | None = None
    stream: bool = False
    tools: list[dict] | None = None
    tool_choice: str | dict | None = None
    response_format: dict | None = None
    dropped: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.dropped is None:
            self.dropped = []

    def as_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"stream": self.stream}
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        if self.top_p is not None:
            kwargs["top_p"] = self.top_p
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens
        if self.stop is not None:
            kwargs["stop"] = self.stop
        if self.tools is not None:
            kwargs["tools"] = self.tools
        if self.tool_choice is not None:
            kwargs["tool_choice"] = self.tool_choice
        if self.response_format is not None:
            kwargs["response_format"] = self.response_format
        return kwargs


def normalize_chat_params(provider_type: str, payload: Any) -> NormalizedParams:
    supported = SUPPORTED_PARAMS.get(provider_type, frozenset(_COMMON))
    params = NormalizedParams(
        temperature=getattr(payload, "temperature", None),
        top_p=getattr(payload, "top_p", None),
        max_tokens=getattr(payload, "max_tokens", None),
        stop=getattr(payload, "stop", None),
        stream=bool(getattr(payload, "stream", False)),
        tools=getattr(payload, "tools", None),
        tool_choice=getattr(payload, "tool_choice", None),
        response_format=getattr(payload, "response_format", None),
    )
    dropped: list[str] = []
    if params.tools is not None and "tools" not in supported:
        dropped.append("tools")
        params.tools = None
        params.tool_choice = None
    if params.tool_choice is not None and "tool_choice" not in supported:
        dropped.append("tool_choice")
        params.tool_choice = None
    if params.response_format is not None and "response_format" not in supported:
        dropped.append("response_format")
        params.response_format = None
    params.dropped = dropped
    return params
