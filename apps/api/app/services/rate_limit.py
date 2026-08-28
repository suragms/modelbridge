"""Redis-backed rate limiting with standard headers."""

from __future__ import annotations

import time
from dataclasses import dataclass

from fastapi import HTTPException

from app.services.redis_client import get_redis


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_at: int


async def _increment(key: str, window_seconds: int) -> tuple[int, int]:
    """Return (count, reset_at) for a fixed window counter."""
    redis = await get_redis()
    now = int(time.time())
    window_start = now - (now % window_seconds)
    reset_at = window_start + window_seconds
    bucket_key = f"{key}:{window_start}"

    pipe = redis.pipeline()
    pipe.incr(bucket_key)
    pipe.expire(bucket_key, window_seconds + 1)
    results = await pipe.execute()
    return int(results[0]), reset_at


async def check_rate_limit(
    *,
    key: str,
    limit: int,
    window_seconds: int,
) -> RateLimitResult:
    if limit <= 0:
        return RateLimitResult(True, 0, 0, int(time.time()) + window_seconds)

    count, reset_at = await _increment(key, window_seconds)
    remaining = max(0, limit - count)
    allowed = count <= limit
    return RateLimitResult(allowed, limit, remaining, reset_at)


def rate_limit_headers(result: RateLimitResult) -> dict[str, str]:
    return {
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(result.remaining),
        "X-RateLimit-Reset": str(result.reset_at),
    }


async def enforce_rate_limits(
    *,
    org_id: str | None,
    api_key_id: str | None,
    user_id: str | None,
    client_ip: str | None,
    per_minute: int,
    per_day: int,
) -> dict[str, str]:
    """Check org/key/ip limits; raise 429 if exceeded. Returns headers from strictest check."""
    checks: list[tuple[str, int, int]] = []
    if org_id:
        checks.append((f"ratelimit:org:{org_id}:min", per_minute, 60))
        checks.append((f"ratelimit:org:{org_id}:day", per_day, 86400))
    if api_key_id:
        checks.append((f"ratelimit:key:{api_key_id}:min", per_minute, 60))
    if user_id:
        checks.append((f"ratelimit:user:{user_id}:min", per_minute, 60))
    if client_ip:
        checks.append((f"ratelimit:ip:{client_ip}:min", per_minute * 2, 60))

    headers: dict[str, str] = {}
    for key, limit, window in checks:
        result = await check_rate_limit(key=key, limit=limit, window_seconds=window)
        headers.update(rate_limit_headers(result))
        if not result.allowed:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Rate limit exceeded",
                    "type": "rate_limit_error",
                },
                headers=headers,
            )
    return headers
