"""Tests for Redis response cache."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.response_cache import (
    CachePolicy,
    ResponseCache,
    build_chat_cache_key,
    build_embedding_cache_key,
    is_chat_cacheable,
    is_embedding_cacheable,
    parse_cache_policy,
)


class TestCachePolicy:
    def test_parse_default(self):
        assert parse_cache_policy(None) == CachePolicy.DEFAULT

    def test_parse_no_cache(self):
        assert parse_cache_policy("no-cache") == CachePolicy.NO_CACHE
        assert parse_cache_policy("no_cache") == CachePolicy.NO_CACHE

    def test_parse_force_cache(self):
        assert parse_cache_policy("force-cache") == CachePolicy.FORCE_CACHE

    def test_parse_bypass(self):
        assert parse_cache_policy("bypass_cache") == CachePolicy.BYPASS_CACHE


class TestCacheKeys:
    def test_chat_key_deterministic(self):
        messages = [{"role": "user", "content": "Hello"}]
        k1 = build_chat_cache_key(org_id="org-1", model="gpt-4", messages=messages)
        k2 = build_chat_cache_key(org_id="org-1", model="gpt-4", messages=messages)
        assert k1 == k2
        assert k1.startswith("mb:cache:chat:")

    def test_chat_key_org_isolation(self):
        messages = [{"role": "user", "content": "Hello"}]
        k1 = build_chat_cache_key(org_id="org-1", model="gpt-4", messages=messages)
        k2 = build_chat_cache_key(org_id="org-2", model="gpt-4", messages=messages)
        assert k1 != k2

    def test_embedding_key_deterministic(self):
        k1 = build_embedding_cache_key(org_id="org-1", model="text-embed", inputs=["hello"])
        k2 = build_embedding_cache_key(org_id="org-1", model="text-embed", inputs=["hello"])
        assert k1 == k2
        assert k1.startswith("mb:cache:embed:")


class TestCacheability:
    def test_chat_not_cacheable_stream(self):
        assert not is_chat_cacheable(stream=True)

    def test_chat_not_cacheable_tools(self):
        assert not is_chat_cacheable(tools=[{"type": "function", "function": {"name": "x"}}])

    def test_chat_cacheable_simple(self):
        assert is_chat_cacheable(stream=False, tools=None, tool_choice=None)

    def test_chat_no_cache_policy(self):
        assert not is_chat_cacheable(policy=CachePolicy.NO_CACHE)

    def test_embedding_cacheable(self):
        assert is_embedding_cacheable()

    def test_embedding_no_cache_policy(self):
        assert not is_embedding_cacheable(policy=CachePolicy.NO_CACHE)


class TestResponseCache:
    @pytest.mark.asyncio
    async def test_get_miss(self):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        cache = ResponseCache()
        with patch("app.services.response_cache.get_redis", AsyncMock(return_value=mock_redis)):
            result = await cache.get("test-key", endpoint="chat")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_hit(self):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value='{"response": {"model": "gpt-4"}}')
        cache = ResponseCache()
        with patch("app.services.response_cache.get_redis", AsyncMock(return_value=mock_redis)):
            result = await cache.get("test-key", endpoint="chat")
        assert result == {"response": {"model": "gpt-4"}}

    @pytest.mark.asyncio
    async def test_set_writes_with_ttl(self):
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock(return_value=True)
        cache = ResponseCache()
        with patch("app.services.response_cache.get_redis", AsyncMock(return_value=mock_redis)):
            ok = await cache.set("test-key", {"data": 1}, endpoint="chat", ttl_seconds=60)
        assert ok is True
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args[0]
        assert args[0] == "test-key"
        assert args[1] == 60

    @pytest.mark.asyncio
    async def test_lookup_bypass(self):
        cache = ResponseCache()
        result = await cache.lookup("key", endpoint="chat", policy=CachePolicy.BYPASS_CACHE)
        assert result is None

    @pytest.mark.asyncio
    async def test_store_skips_no_cache(self):
        cache = ResponseCache()
        ok = await cache.store("key", {"x": 1}, endpoint="chat", policy=CachePolicy.NO_CACHE)
        assert ok is False

    @pytest.mark.asyncio
    async def test_redis_error_returns_none(self):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=ConnectionError("redis down"))
        cache = ResponseCache()
        with patch("app.services.response_cache.get_redis", AsyncMock(return_value=mock_redis)):
            result = await cache.get("test-key", endpoint="embeddings")
        assert result is None


class TestSemanticCache:
    @pytest.mark.asyncio
    async def test_disabled_by_default(self):
        from app.services.semantic_cache import get_semantic_cache

        backend = get_semantic_cache()
        assert await backend.lookup("hello", threshold=0.9) is None
