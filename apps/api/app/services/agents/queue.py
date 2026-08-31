"""Enqueue agent and workflow jobs via ARQ."""

from __future__ import annotations

import structlog
from arq import create_pool
from arq.connections import RedisSettings

from app.config import get_settings

logger = structlog.get_logger()
_pool = None


async def get_arq_pool():
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _pool


async def enqueue_agent_execution(execution_id: str) -> bool:
    try:
        pool = await get_arq_pool()
        await pool.enqueue_job("execute_agent_job", execution_id)
        return True
    except Exception as e:
        logger.warning("agent_enqueue_failed", execution_id=execution_id, error=str(e))
        return False


async def enqueue_workflow_execution(execution_id: str) -> bool:
    try:
        pool = await get_arq_pool()
        await pool.enqueue_job("execute_workflow_job", execution_id)
        return True
    except Exception as e:
        logger.warning("workflow_enqueue_failed", execution_id=execution_id, error=str(e))
        return False
