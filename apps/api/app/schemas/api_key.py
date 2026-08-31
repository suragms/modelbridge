from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.api_key import ALL_API_KEY_SCOPES


class APIKeyCreate(BaseModel):
    name: str
    expires_in_days: int | None = None
    scopes: list[str] = Field(default_factory=list)
    monthly_token_limit: int | None = Field(default=None, ge=0)
    monthly_budget_usd: float | None = Field(default=None, ge=0)


class APIKeyCreated(BaseModel):
    id: uuid.UUID
    key: str
    key_prefix: str
    name: str
    scopes: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class APIKeyResponse(BaseModel):
    id: uuid.UUID
    key_prefix: str
    name: str
    is_active: bool
    scopes: list[str]
    expires_at: datetime | None
    monthly_token_limit: int | None = None
    monthly_budget_usd: float | None = None
    created_at: datetime
    last_used_at: datetime | None
    last_used_ip: str | None = None

    model_config = {"from_attributes": True}
