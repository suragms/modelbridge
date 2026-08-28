"""Semantic cache abstraction (feature-flagged, not yet implemented).

Semantic caching matches requests by embedding similarity rather than exact
hash equality. This module defines the interface and guards against
accidental use while the feature is disabled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.config import get_settings


@dataclass
class SemanticCacheResult:
    key: str
    similarity: float
    value: dict[str, Any]


class SemanticCacheBackend(Protocol):
    async def lookup(self, text: str, *, threshold: float) -> SemanticCacheResult | None: ...
    async def store(self, text: str, value: dict[str, Any]) -> None: ...


class DisabledSemanticCache:
    """No-op backend used when semantic caching is disabled."""

    async def lookup(self, text: str, *, threshold: float) -> SemanticCacheResult | None:
        return None

    async def store(self, text: str, value: dict[str, Any]) -> None:
        return None


def get_semantic_cache() -> SemanticCacheBackend:
    settings = get_settings()
    if not settings.semantic_cache_enabled:
        return DisabledSemanticCache()
    # Future: plug in vector-store backend (Redis Stack, pgvector, etc.)
    return DisabledSemanticCache()
