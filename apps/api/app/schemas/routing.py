from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class RoutingPolicyCreate(BaseModel):
    name: str
    description: str | None = None
    strategy: str = "auto"
    config: dict | None = None
    is_default: bool = False


class RoutingPolicyResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    strategy: str
    is_default: bool
    config: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
