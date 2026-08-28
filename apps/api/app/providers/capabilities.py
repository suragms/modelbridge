"""Conservative capability inference from provider-reported model ids.

Unknown models default to chat+streaming only. Embedding/vision/tools flags
are set only when the model id clearly indicates the capability. This is not
a substitute for provider-reported capability APIs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class InferredCapabilities:
    supports_chat: bool = True
    supports_streaming: bool = True
    supports_embeddings: bool = False
    supports_tools: bool = False
    supports_tool_choice: bool = False
    supports_vision: bool = False
    supports_json_mode: bool = False
    supports_structured_output: bool = False
    supports_reasoning: bool = False
    embedding_dimensions: int | None = None
    max_output_tokens: int | None = None
    context_window: int = 4096


_EMBED_HINTS = ("embed", "embedding", "bge-", "e5-", "minilm", "nomic-embed", "mxbai-embed")
_NON_CHAT_HINTS = ("whisper", "tts-", "dall-e", "dalle", "moderation", "sora-", "canary")
_VISION_HINTS = (
    "gpt-4o",
    "gpt-4.1",
    "gpt-4-turbo",
    "gpt-4-vision",
    "vision",
    "llava",
    "claude-3",
    "claude-sonnet",
    "claude-haiku",
    "claude-opus",
    "gemini-1.5",
    "gemini-2",
    "gemini-pro-vision",
)
_TOOL_HINTS = ("gpt-4", "gpt-3.5", "gpt-4o", "o1", "o3", "o4", "claude", "gemini", "llama-3", "llama3")
_JSON_HINTS = ("gpt-4", "gpt-3.5-turbo", "gpt-4o", "o1", "o3", "gemini")
_REASONING_HINTS = ("o1", "o3", "o4-mini", "deepseek-r1", "qwq")
_STRUCTURED_HINTS = ("gpt-4o", "gpt-4.1", "o1", "o3", "gpt-4o-mini")


def _contains_any(model_id: str, hints: tuple[str, ...]) -> bool:
    return any(h in model_id for h in hints)


def infer_capabilities(model_id: str, provider_type: str = "openai") -> InferredCapabilities:
    mid = (model_id or "").lower()
    caps = InferredCapabilities()

    is_embed = _contains_any(mid, _EMBED_HINTS)
    is_non_chat = _contains_any(mid, _NON_CHAT_HINTS)

    if is_embed:
        caps.supports_chat = False
        caps.supports_streaming = False
        caps.supports_embeddings = True
        caps.supports_tools = False
        caps.supports_vision = False
        caps.supports_json_mode = False
        if "3-small" in mid or "3.small" in mid:
            caps.embedding_dimensions = 1536
        elif "3-large" in mid:
            caps.embedding_dimensions = 3072
        elif "ada-002" in mid:
            caps.embedding_dimensions = 1536
        return caps

    if is_non_chat:
        caps.supports_chat = False
        caps.supports_streaming = False
        return caps

    if provider_type in {"openai", "openrouter", "groq", "custom", "lmstudio"}:
        caps.supports_tools = _contains_any(mid, _TOOL_HINTS) and not is_embed
        caps.supports_tool_choice = caps.supports_tools
        caps.supports_vision = _contains_any(mid, _VISION_HINTS)
        caps.supports_json_mode = _contains_any(mid, _JSON_HINTS)
        caps.supports_structured_output = _contains_any(mid, _STRUCTURED_HINTS)
        caps.supports_reasoning = _contains_any(mid, _REASONING_HINTS)
        if "gpt-4o" in mid or "gpt-4.1" in mid:
            caps.context_window = 128000
            caps.max_output_tokens = 16384
        elif "gpt-4" in mid:
            caps.context_window = 8192
        elif "gpt-3.5" in mid:
            caps.context_window = 16385
    elif provider_type == "ollama":
        caps.supports_vision = "llava" in mid or "vision" in mid
        caps.supports_tools = False
        caps.supports_json_mode = False
    else:
        # Unknown provider: chat + streaming only.
        pass

    return caps
