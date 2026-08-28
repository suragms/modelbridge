"""Token quota enforcement with Redis coordination."""

from __future__ import annotations

import time
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.request_log import RequestLog, UsageRecord
from app.services.redis_client import get_redis


def _month_key(prefix: str, entity_id: str) -> str:
    month = datetime.now(UTC).strftime("%Y%m")
    return f"quota:{prefix}:{entity_id}:{month}"


async def _reserve_tokens(redis_key: str, limit: int, requested: int) -> None:
    """Atomically reserve tokens using Redis; falls back to DB count on cold start."""
    redis = await get_redis()
    script = """
    local current = tonumber(redis.call('GET', KEYS[1]) or '0')
    local add = tonumber(ARGV[1])
    local limit = tonumber(ARGV[2])
    if limit <= 0 then return 1 end
    if current + add > limit then return 0 end
    redis.call('INCRBY', KEYS[1], add)
    redis.call('EXPIRE', KEYS[1], ARGV[3])
    return 1
    """
    ttl = 60 * 60 * 24 * 35  # ~35 days
    ok = await redis.eval(script, 1, redis_key, requested, limit, ttl)
    if ok == 0:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "QUOTA_EXCEEDED",
                "message": "Monthly token quota exceeded",
                "type": "quota_error",
            },
        )


async def _db_monthly_tokens(
    db: AsyncSession,
    *,
    organization_id,
    api_key_id=None,
) -> int:
    month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    q = (
        select(func.coalesce(func.sum(UsageRecord.total_tokens), 0))
        .join(RequestLog, RequestLog.request_id == UsageRecord.request_id)
        .where(RequestLog.created_at >= month_start)
    )
    if api_key_id:
        q = q.where(RequestLog.api_key_id == api_key_id)
    elif organization_id:
        q = q.where(RequestLog.organization_id == organization_id)
    result = await db.execute(q)
    return int(result.scalar_one() or 0)


async def check_token_quota(
    db: AsyncSession,
    *,
    organization_id,
    api_key_id=None,
    org_monthly_limit: int | None,
    key_monthly_limit: int | None,
    estimated_tokens: int = 1,
) -> None:
    """Pre-request quota check with Redis reservation to reduce concurrent bypass."""
    if key_monthly_limit and key_monthly_limit > 0:
        key = _month_key("key", str(api_key_id))
        await _reserve_tokens(key, key_monthly_limit, estimated_tokens)

    if org_monthly_limit and org_monthly_limit > 0:
        key = _month_key("org", str(organization_id))
        await _reserve_tokens(key, org_monthly_limit, estimated_tokens)


async def sync_quota_from_db(
    db: AsyncSession,
    *,
    organization_id,
    api_key_id=None,
) -> int:
    """Return current month token usage (for display)."""
    return await _db_monthly_tokens(
        db, organization_id=organization_id, api_key_id=api_key_id
    )
