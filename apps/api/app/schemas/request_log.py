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
    requested_model: str | None = None
    selected_model: str | None = None
    routing_policy: str | None = None
    candidates_count: int | None = None
    fallback_count: int | None = None
    provider_latency_ms: float | None = None
    completed_at: datetime | None = None
    error_code: str | None = None
    error_type: str | None = None
    created_at: datetime

    # Joined fields (optional)
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    usage_source: str | None = None
    estimated_total_cost: float | None = None

    model_config = {"from_attributes": True}


class RequestLogListResponse(BaseModel):
    items: list[RequestLogResponse]
    total: int
    limit: int
    offset: int


class RequestDetailResponse(RequestLogResponse):
    estimated_input_cost: float | None = None
    estimated_output_cost: float | None = None
    cost_is_estimated: bool | None = None
    pricing_source: str | None = None
    currency: str | None = None
    cost_disclaimer: str = "Estimated cost — may not match provider invoices."


class UsageResponse(BaseModel):
    id: uuid.UUID
    request_id: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    usage_source: str
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
    pricing_source: str
    currency: str
    created_at: datetime

    model_config = {"from_attributes": True}
