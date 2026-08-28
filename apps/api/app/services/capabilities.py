"""Capability detection, filtering reasons, and gateway capability errors."""

from __future__ import annotations

from fastapi import HTTPException

from app.models.model import Model
from app.models.provider import Provider, ProviderStatus

KNOWN_CAPABILITIES = frozenset({
    "chat",
    "streaming",
    "embeddings",
    "tools",
    "tool_choice",
    "vision",
    "json_mode",
    "structured_output",
    "reasoning",
})

_CAPABILITY_COLUMNS = {
    "chat": "supports_chat",
    "streaming": "supports_streaming",
    "tools": "supports_tools",
    "tool_choice": "supports_tool_choice",
    "vision": "supports_vision",
    "embeddings": "supports_embeddings",
    "json_mode": "supports_json_mode",
    "structured_output": "supports_structured_output",
    "reasoning": "supports_reasoning",
}

_CAPABILITY_ERRORS = {
    "chat": "NO_COMPATIBLE_MODEL",
    "embeddings": "EMBEDDINGS_NOT_SUPPORTED",
    "tools": "TOOLS_NOT_SUPPORTED",
    "tool_choice": "TOOLS_NOT_SUPPORTED",
    "vision": "VISION_NOT_SUPPORTED",
    "json_mode": "STRUCTURED_OUTPUT_NOT_SUPPORTED",
    "structured_output": "STRUCTURED_OUTPUT_NOT_SUPPORTED",
    "streaming": "CAPABILITY_NOT_SUPPORTED",
    "reasoning": "CAPABILITY_NOT_SUPPORTED",
}


def capability_error_code(required: set[str]) -> str:
    for cap in ("vision", "tools", "embeddings", "structured_output", "json_mode"):
        if cap in required:
            return _CAPABILITY_ERRORS[cap]
    return "NO_COMPATIBLE_MODEL"


def raise_no_compatible_model(required: set[str], requested_model: str | None = None) -> None:
    code = capability_error_code(required)
    caps = ", ".join(sorted(required)) or "chat"
    if requested_model and requested_model != "auto":
        message = (
            f"Model '{requested_model}' is unavailable or does not support "
            f"required capabilities: {caps}"
        )
    else:
        message = f"No compatible model found for required capabilities: {caps}"
    raise HTTPException(
        status_code=400 if code != "NO_COMPATIBLE_MODEL" else 503,
        detail={"code": code, "message": message, "type": "capability_error"},
    )


def detect_chat_capabilities(
    messages: list,
    tools: list | None = None,
    tool_choice: str | dict | None = None,
    response_format: dict | None = None,
    stream: bool = False,
) -> set[str]:
    caps: set[str] = {"chat"}
    if tools:
        caps.add("tools")
    if tool_choice not in (None, "none", "auto"):
        caps.add("tools")
        caps.add("tool_choice")
    if stream:
        caps.add("streaming")
    rf = response_format or {}
    rf_type = rf.get("type")
    if rf_type == "json_object":
        caps.add("json_mode")
    elif rf_type == "json_schema" or rf.get("json_schema"):
        caps.add("json_mode")
        caps.add("structured_output")
    if _messages_contain_image(messages):
        caps.add("vision")
    return caps


def _messages_contain_image(messages: list) -> bool:
    for msg in messages:
        content = msg.content if hasattr(msg, "content") else (msg.get("content") if isinstance(msg, dict) else None)
        if isinstance(content, list):
            for part in content:
                if not isinstance(part, dict):
                    continue
                ptype = part.get("type")
                if ptype in {"image_url", "image", "input_image"}:
                    return True
                if "image_url" in part:
                    return True
    return False


def collect_image_urls(messages: list) -> list[str]:
    urls: list[str] = []
    for msg in messages:
        content = msg.content if hasattr(msg, "content") else (msg.get("content") if isinstance(msg, dict) else None)
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            image = part.get("image_url")
            if isinstance(image, dict) and image.get("url"):
                urls.append(str(image["url"]))
            elif isinstance(image, str):
                urls.append(image)
            elif part.get("type") == "image_url" and isinstance(part.get("url"), str):
                urls.append(part["url"])
    return urls


def _model_flag(model: Model, attr: str, default: bool = False) -> bool:
    value = getattr(model, attr, default)
    if value is None:
        return default
    return bool(value)


def model_capability_map(model: Model) -> dict[str, bool]:
    return {
        "chat": _model_flag(model, "supports_chat", default=True),
        "streaming": _model_flag(model, "supports_streaming", default=True),
        "embeddings": _model_flag(model, "supports_embeddings"),
        "tools": _model_flag(model, "supports_tools"),
        "tool_choice": _model_flag(model, "supports_tool_choice") or _model_flag(model, "supports_tools"),
        "vision": _model_flag(model, "supports_vision"),
        "json_mode": _model_flag(model, "supports_json_mode"),
        "structured_output": _model_flag(model, "supports_structured_output"),
        "reasoning": _model_flag(model, "supports_reasoning"),
    }


def missing_capabilities(model: Model, required: set[str]) -> list[str]:
    mapping = model_capability_map(model)
    missing: list[str] = []
    for cap in required:
        if cap == "tool_choice" and mapping.get("tools"):
            continue
        if not mapping.get(cap, cap not in _CAPABILITY_COLUMNS):
            missing.append(cap)
    return missing


def filter_reason(model: Model, provider: Provider | None, required: set[str]) -> str | None:
    """Return why a model would be filtered, or None if it is eligible."""
    if not model.is_enabled:
        return "Model is disabled"
    if provider is None:
        return "Provider not found"
    if not provider.is_enabled:
        return "Provider is disabled"
    if provider.status == ProviderStatus.OFFLINE:
        return "Provider is offline"
    missing = missing_capabilities(model, required)
    if missing:
        labels = ", ".join(missing)
        return f"Does not support {labels}"
    return None
