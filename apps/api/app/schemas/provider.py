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
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProviderTestResult(BaseModel):
    success: bool
    message: str
    latency_ms: float | None = None
    models_found: list[str] = []
