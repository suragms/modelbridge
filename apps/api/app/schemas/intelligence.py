"""Intelligence layer API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RecommendationResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    category: str
    severity: str
    title: str
    description: str
    evidence: dict
    suggested_action: str | None
    confidence: float
    risks: str | None
    policy_constraints: dict | None
    automation_level: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RecommendationActionRequest(BaseModel):
    notes: str | None = None


class AnomalyResponse(BaseModel):
    id: str
    metric: str
    dimension: str | None
    observed_value: float
    expected_min: float | None
    expected_max: float | None
    deviation: float | None
    severity: str
    status: str
    evidence: dict
    detected_at: str


class AssistantQueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)


class AssistantQueryResponse(BaseModel):
    status: str
    question: str | None = None
    answer: str | None = None
    interpretation: str | None = None
    evidence_sources: list[str] = Field(default_factory=list)
    confidence: float = 0
    time_range: str | None = None
    message: str | None = None
    data: dict | None = None
