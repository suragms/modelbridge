from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class RoutingPolicyCreate(BaseModel):
    name: str
    description: str | None = None
    strategy: str = "auto"
    config: dict[str, Any] | None = None
    is_default: bool = False


class RoutingPolicyUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    strategy: str | None = None
    config: dict[str, Any] | None = None
    is_default: bool | None = None


class RoutingPolicyResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    strategy: str
    is_default: bool
    config: dict | None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class RoutingTestRequest(BaseModel):
    requested_model: str = "auto"
    required_capabilities: list[str] | None = None
    strategy: str | None = None
    policy_name: str | None = None


class RouteCandidate(BaseModel):
    model_id: uuid.UUID
    model_name: str
    provider_name: str
    provider_type: str
    score: float
    latency_ms: float
    cost_per_1k: float
    is_local: bool


class RoutingTestResponse(BaseModel):
    candidates: list[RouteCandidate]
    filtered: list[RouteCandidate]
    selected: RouteCandidate | None
    strategy: str
    reason: str
    fallback_order: list[str]
