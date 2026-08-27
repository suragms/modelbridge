from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class RequestLogResponse(BaseModel):
    id: uuid.UUID
    request_id: str
    model: str
    provider: str
    latency_ms: float
    status: str
    error: str | None
    routing_strategy: str | None
    fallback_used: bool
    # Routing decision metadata (no prompt content is ever stored).
    requested_model: str | None = None
    routing_policy: str | None = None
    candidates_count: int | None = None
    fallback_count: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UsageResponse(BaseModel):
    id: uuid.UUID
    request_id: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CostResponse(BaseModel):
    id: uuid.UUID
    request_id: str
    model: str
    provider: str
    input_cost: float
    output_cost: float
    total_cost: float
    is_estimated: bool
    created_at: datetime

    model_config = {"from_attributes": True}
