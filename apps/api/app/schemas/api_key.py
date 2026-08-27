from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class APIKeyCreate(BaseModel):
    name: str
    expires_in_days: int | None = None


class APIKeyCreated(BaseModel):
    id: uuid.UUID
    key: str
    key_prefix: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class APIKeyResponse(BaseModel):
    id: uuid.UUID
    key_prefix: str
    name: str
    is_active: bool
    expires_at: datetime | None
    created_at: datetime
    last_used_at: datetime | None

    model_config = {"from_attributes": True}
