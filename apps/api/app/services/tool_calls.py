"""Normalize provider tool-call payloads into an OpenAI-compatible shape.

ModelBridge is a gateway: it never executes client-supplied tools.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class InternalToolCall:
    id: str
    name: str
    arguments: str
    type: str = "function"
    provider_metadata: dict[str, Any] = field(default_factory=dict)


def _as_arguments(value: Any) -> str:
    if value is None:
        return "{}"
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value)
    except (TypeError, ValueError):
        return "{}"


def normalize_tool_call(raw: dict, index: int = 0) -> InternalToolCall:
    """Accept OpenAI, Anthropic-like, and generic function-call dicts."""
    fn = raw.get("function") or {}
    name = fn.get("name") or raw.get("name") or raw.get("function_name") or f"tool_{index}"
    arguments = fn.get("arguments", raw.get("arguments", raw.get("input", "{}")))
    call_id = raw.get("id") or raw.get("tool_call_id") or f"call_{index}"
    return InternalToolCall(
        id=str(call_id),
        name=str(name),
        arguments=_as_arguments(arguments),
        type=raw.get("type", "function"),
        provider_metadata={k: v for k, v in raw.items() if k not in {"id", "function", "type"}},
    )


def to_openai_tool_call(call: InternalToolCall) -> dict:
    return {
        "id": call.id,
        "type": "function",
        "function": {"name": call.name, "arguments": call.arguments},
    }


def normalize_message_tool_calls(message: dict) -> dict:
    """Return a copy of ``message`` with tool_calls in OpenAI format."""
    out = dict(message)
    raw_calls = out.get("tool_calls") or []
    if not raw_calls and out.get("function_call"):
        raw_calls = [{"type": "function", "function": out["function_call"]}]
    if not raw_calls:
        return out
    normalized = [
        to_openai_tool_call(normalize_tool_call(c, i))
        for i, c in enumerate(raw_calls)
        if isinstance(c, dict)
    ]
    if normalized:
        out["tool_calls"] = normalized
    return out
