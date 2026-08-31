"""Cache and queue resilience helpers."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()


async def redis_available() -> bool:
    try:
        from app.services.redis_client import get_redis

        client = await get_redis()
        await client.ping()
        return True
    except Exception as e:
        logger.warning("redis_unavailable", error=str(e))
        return False


async def with_cache_fallback(operation, fallback):
    """Run cache operation; on failure return fallback without breaking correctness."""
    try:
        if not await redis_available():
            return fallback
        return await operation()
    except Exception as e:
        logger.warning("cache_operation_failed", error=str(e))
        return fallback


async def enqueue_with_fallback(enqueue_fn, inline_fn):
    """Try queue enqueue; run inline fallback if queue unavailable."""
    try:
        if not await redis_available():
            logger.warning("queue_unavailable_inline_fallback")
            return await inline_fn()
        return await enqueue_fn()
    except Exception as e:
        logger.warning("queue_enqueue_failed", error=str(e))
        return await inline_fn()
