from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PolicyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    policy_type: str
    status: str = "draft"
    priority: int = Field(default=100, ge=1, le=10000)
    rules: dict[str, Any] = Field(default_factory=dict)
    action: str = "deny"


class PolicyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    policy_type: str | None = None
    status: str | None = None
    priority: int | None = Field(default=None, ge=1, le=10000)
    rules: dict[str, Any] | None = None
    action: str | None = None
    change_summary: str | None = None


class PolicyResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    policy_type: str
    status: str
    priority: int
    rules: dict[str, Any]
    action: str
    version: int
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PolicyVersionResponse(BaseModel):
    id: UUID
    policy_id: UUID
    version: int
    action: str
    rules: dict[str, Any]
    status: str
    priority: int
    change_summary: str | None
    changed_by: UUID | None
    changed_at: datetime

    model_config = {"from_attributes": True}


class SimulateRequest(BaseModel):
    model: str = "auto"
    messages: list[dict[str, Any]] = Field(default_factory=list)
    input: str | None = None
    tools: list[dict] | None = None
    stream: bool = False
    request_type: str = "chat"


class SimulateResponse(BaseModel):
    decision: str
    reason: str
    classification: str
    risk_level: str
    risk_reasons: list[str]
    detection_categories: list[str]
    matched_policies: list[dict[str, Any]]
    restrictions: dict[str, Any]
    policy_fingerprint: str


class EventResponse(BaseModel):
    id: UUID
    event_type: str
    decision: str | None
    policy_id: UUID | None
    policy_name: str | None
    policy_type: str | None
    reason: str | None
    risk_level: str | None
    classification: str | None
    detection_categories: list | None
    requested_model: str | None
    request_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApprovalResponse(BaseModel):
    id: UUID
    status: str
    request_type: str
    risk_level: str | None
    classification: str | None
    matched_policy_name: str | None
    requested_model: str | None
    requester_id: UUID | None
    reviewer_id: UUID | None
    review_comment: str | None
    safe_snapshot: dict | None
    expires_at: datetime | None
    created_at: datetime
    reviewed_at: datetime | None

    model_config = {"from_attributes": True}


class ApprovalReview(BaseModel):
    comment: str | None = None


class SettingsUpdate(BaseModel):
    pii_detection_enabled: bool | None = None
    secret_detection_enabled: bool | None = None
    redact_prompts: bool | None = None
    redact_responses: bool | None = None
    block_on_secret: bool | None = None
    block_sensitive_to_cloud: bool | None = None
    require_local_for_high_risk: bool | None = None
    allow_cloud_providers: bool | None = None
    allow_local_providers: bool | None = None
    content_safety_enabled: bool | None = None
    approval_enabled: bool | None = None
    approval_ttl_hours: int | None = Field(default=None, ge=1, le=168)


class SettingsResponse(BaseModel):
    organization_id: UUID
    pii_detection_enabled: bool
    secret_detection_enabled: bool
    redact_prompts: bool
    redact_responses: bool
    block_on_secret: bool
    block_sensitive_to_cloud: bool
    require_local_for_high_risk: bool
    allow_cloud_providers: bool
    allow_local_providers: bool
    content_safety_enabled: bool
    approval_enabled: bool
    approval_ttl_hours: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationResponse(BaseModel):
    id: UUID
    title: str
    body: str
    severity: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OverviewResponse(BaseModel):
    active_policies: int
    blocked_requests: int
    warnings: int
    sensitive_events: int
    pending_approvals: int
    risk_distribution: dict[str, int]
    top_policies: list[dict[str, Any]]
    recent_events: list[EventResponse]


class ReportResponse(BaseModel):
    start: datetime | None = None
    end: datetime | None = None
    policy_matches: int
    blocked_requests: int
    warnings: int
    sensitive_data_events: int
    approvals: int
    by_risk: dict[str, int]
    by_event_type: dict[str, int]
