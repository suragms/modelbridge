"""Redis-backed exact response cache for chat and embeddings.

Cache keys are deterministic hashes of request content and parameters.
Organization-scoped to preserve tenant isolation.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any

from app.config import get_settings
from app.services.metrics import record_cache_event
from app.services.redis_client import get_redis


class CachePolicy(str, Enum):
    NO_CACHE = "no_cache"
    DEFAULT = "default"
    FORCE_CACHE = "force_cache"
    BYPASS_CACHE = "bypass_cache"


def parse_cache_policy(header_value: str | None) -> CachePolicy:
    if not header_value:
        return CachePolicy.DEFAULT
    normalized = header_value.strip().lower().replace("-", "_")
    mapping = {
        "no_cache": CachePolicy.NO_CACHE,
        "no-cache": CachePolicy.NO_CACHE,
        "default": CachePolicy.DEFAULT,
        "force_cache": CachePolicy.FORCE_CACHE,
        "force-cache": CachePolicy.FORCE_CACHE,
        "bypass_cache": CachePolicy.BYPASS_CACHE,
        "bypass-cache": CachePolicy.BYPASS_CACHE,
    }
    return mapping.get(normalized, CachePolicy.DEFAULT)


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _hash_payload(payload: dict) -> str:
    return hashlib.sha256(_stable_json(payload).encode()).hexdigest()


def build_chat_cache_key(
    *,
    org_id: str | None,
    model: str,
    messages: list,
    temperature: float | None = None,
    top_p: float | None = None,
    max_tokens: int | None = None,
    stop: str | list[str] | None = None,
    response_format: dict | None = None,
) -> str:
    settings = get_settings()
    normalized_messages = []
    for m in messages:
        if hasattr(m, "model_dump"):
            normalized_messages.append(m.model_dump(exclude_none=True))
        elif isinstance(m, dict):
            normalized_messages.append(m)
        else:
            normalized_messages.append({"role": m.role, "content": m.content})

    payload = {
        "endpoint": "chat",
        "org_id": org_id or "global",
        "model": model,
        "messages": normalized_messages,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "stop": stop,
        "response_format": response_format,
    }
    digest = _hash_payload(payload)
    return f"{settings.cache_key_prefix}:chat:{digest}"


def build_embedding_cache_key(
    *,
    org_id: str | None,
    model: str,
    inputs: list[str],
    encoding_format: str = "float",
) -> str:
    settings = get_settings()
    payload = {
        "endpoint": "embeddings",
        "org_id": org_id or "global",
        "model": model,
        "inputs": inputs,
        "encoding_format": encoding_format,
    }
    digest = _hash_payload(payload)
    return f"{settings.cache_key_prefix}:embed:{digest}"


def is_chat_cacheable(
    *,
    stream: bool = False,
    tools: list | None = None,
    tool_choice: str | dict | None = None,
    policy: CachePolicy = CachePolicy.DEFAULT,
) -> bool:
    settings = get_settings()
    if not settings.cache_enabled or policy == CachePolicy.NO_CACHE:
        return False
    if stream:
        return False
    if tools:
        return False
    if tool_choice not in (None, "none", "auto"):
        return False
    return True


def is_embedding_cacheable(*, policy: CachePolicy = CachePolicy.DEFAULT) -> bool:
    settings = get_settings()
    return settings.cache_enabled and policy != CachePolicy.NO_CACHE


class ResponseCache:
    """Exact-match response cache backed by Redis."""

    async def get(self, key: str, *, endpoint: str) -> dict | None:
        settings = get_settings()
        if not settings.cache_enabled:
            return None
        try:
            redis = await get_redis()
            raw = await redis.get(key)
            if raw is None:
                record_cache_event("miss", endpoint)
                return None
            record_cache_event("hit", endpoint)
            return json.loads(raw)
        except Exception:
            record_cache_event("error", endpoint)
            return None

    async def set(
        self,
        key: str,
        value: dict,
        *,
        endpoint: str,
        ttl_seconds: int | None = None,
    ) -> bool:
        settings = get_settings()
        if not settings.cache_enabled:
            return False
        ttl = ttl_seconds
        if ttl is None:
            ttl = (
                settings.chat_cache_ttl_seconds
                if endpoint == "chat"
                else settings.embedding_cache_ttl_seconds
            )
        try:
            redis = await get_redis()
            await redis.setex(key, ttl, _stable_json(value))
            record_cache_event("write", endpoint)
            return True
        except Exception:
            record_cache_event("error", endpoint)
            return False

    async def lookup(
        self,
        key: str,
        *,
        endpoint: str,
        policy: CachePolicy,
    ) -> dict | None:
        if policy in (CachePolicy.NO_CACHE, CachePolicy.BYPASS_CACHE):
            record_cache_event("bypass", endpoint)
            return None
        return await self.get(key, endpoint=endpoint)

    async def store(
        self,
        key: str,
        value: dict,
        *,
        endpoint: str,
        policy: CachePolicy,
    ) -> bool:
        if policy == CachePolicy.NO_CACHE:
            return False
        if policy == CachePolicy.FORCE_CACHE:
            # FORCE_CACHE is read-only from client perspective
            return False
        return await self.set(key, value, endpoint=endpoint)


def get_response_cache() -> ResponseCache:
    return ResponseCache()
