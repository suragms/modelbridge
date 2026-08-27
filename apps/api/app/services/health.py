"""Persistent provider health monitoring.

Phase 2 implements the health-check architecture plus a reliable manual check
(the ``POST /providers/{id}/test`` endpoint). Background/periodic monitoring is
a documented future enhancement and is NOT claimed to exist here.
"""

from __future__ import annotations

import time
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health import HealthCheck
from app.models.provider import Provider, ProviderStatus
from app.providers.base import AIProvider
from app.providers.registry import get_provider_registry

# Number of recent checks used to compute a rolling success rate.
_RECENT_WINDOW = 20


class HealthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_provider(self, provider: Provider, api_key: str | None = None) -> dict:
        """Run a health check against a provider and persist the result.

        Returns a dict describing the outcome:
        ``{"success", "latency_ms", "message", "status"}``.
        """
        registry = get_provider_registry()
        try:
            ai_provider = registry.create_provider(
                provider_type=provider.type,
                api_key=api_key,
                base_url=provider.base_url,
            )
        except ValueError as e:
            return await self._record(
                provider, ProviderStatus.UNKNOWN, 0.0, f"Unsupported provider type: {e}"
            )

        start = time.time()
        try:
            healthy = await ai_provider.health_check()
        except Exception as e:  # defensive: providers should not raise, but never trust that
            healthy = False
            message = f"Health check raised: {e}"
        else:
            message = "Provider is healthy" if healthy else "Provider is unreachable"
        latency = (time.time() - start) * 1000

        status = ProviderStatus.HEALTHY if healthy else ProviderStatus.OFFLINE
        return await self._record(provider, status, latency, "" if healthy else message, success=healthy)

    async def _record(
        self,
        provider: Provider,
        status: ProviderStatus,
        latency_ms: float,
        error: str,
        success: bool | None = None,
    ) -> dict:
        if success is None:
            success = status == ProviderStatus.HEALTHY

        # Persist the individual check.
        check = HealthCheck(
            status=status.value,
            latency_ms=latency_ms,
            error=error or None,
            provider_id=provider.id,
        )
        self.db.add(check)

        # Update aggregate counters on the provider.
        provider.status = status
        provider.last_health_check_at = _utcnow()
        provider.last_health_latency_ms = latency_ms
        provider.total_health_checks = (provider.total_health_checks or 0) + 1
        if not success:
            provider.failed_health_checks = (provider.failed_health_checks or 0) + 1

        await self.db.flush()
        return {
            "success": success,
            "latency_ms": latency_ms,
            "message": error or ("Provider is healthy" if success else "Provider is unhealthy"),
            "status": status.value,
        }

    async def recent_success_rate(self, provider_id: uuid.UUID) -> float | None:
        """Return the recent success rate (0..1) over the last N checks, or None."""
        result = await self.db.execute(
            select(HealthCheck)
            .where(HealthCheck.provider_id == provider_id)
            .order_by(HealthCheck.checked_at.desc())
            .limit(_RECENT_WINDOW)
        )
        checks = list(result.scalars().all())
        if not checks:
            return None
        healthy = sum(1 for c in checks if c.status == ProviderStatus.HEALTHY.value)
        return healthy / len(checks)

    async def average_latency(self, provider_id: uuid.UUID) -> float | None:
        """Return the average latency over the last N checks, or None."""
        result = await self.db.execute(
            select(HealthCheck)
            .where(HealthCheck.provider_id == provider_id)
            .order_by(HealthCheck.checked_at.desc())
            .limit(_RECENT_WINDOW)
        )
        checks = list(result.scalars().all())
        if not checks:
            return None
        return sum(c.latency_ms for c in checks) / len(checks)


def _utcnow():
    from datetime import UTC, datetime

    return datetime.now(UTC)
