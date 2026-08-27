from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ProviderCreate(BaseModel):
    name: str
    type: str
    base_url: str | None = None
    api_key: str | None = None
    config: dict | None = None


class ProviderUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    is_enabled: bool | None = None
    config: dict | None = None


class ProviderResponse(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    base_url: str | None
    status: str
    is_enabled: bool
    config: dict | None
    # Never the secret itself — only whether a stored key exists (for UI masking).
    has_api_key: bool = False
    last_health_check_at: datetime | None = None
    last_health_latency_ms: float | None = None
    total_health_checks: int = 0
    failed_health_checks: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate_from_provider(cls, provider):
        """Build a response without ever exposing the stored credential."""
        data = {
            "id": provider.id,
            "name": provider.name,
            "type": provider.type,
            "base_url": provider.base_url,
            "status": provider.status,
            "is_enabled": provider.is_enabled,
            "config": provider.config,
            "has_api_key": bool(provider.credentials),
            "last_health_check_at": provider.last_health_check_at,
            "last_health_latency_ms": provider.last_health_latency_ms,
            "total_health_checks": provider.total_health_checks or 0,
            "failed_health_checks": provider.failed_health_checks or 0,
            "created_at": provider.created_at,
            "updated_at": provider.updated_at,
        }
        return cls.model_validate(data)


class ProviderTestResult(BaseModel):
    success: bool
    message: str
    latency_ms: float | None = None
    models_found: list[str] = []
