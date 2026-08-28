from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    created_at: datetime
    updated_at: datetime | None = None
    role: str | None = None

    model_config = {"from_attributes": True}


class OrganizationMemberResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    full_name: str | None
    role: str
    created_at: datetime


class OrganizationMemberUpdate(BaseModel):
    role: str


class OrganizationInviteCreate(BaseModel):
    role: str = "member"
    email_hint: str | None = None
    expires_in_days: int = 7


class OrganizationInviteResponse(BaseModel):
    id: uuid.UUID
    role: str
    email_hint: str | None
    expires_at: datetime
    invite_url: str
    token: str  # shown once


class OrganizationSettingsResponse(BaseModel):
    organization_id: uuid.UUID
    rate_limit_per_minute: int
    rate_limit_per_day: int
    monthly_token_limit: int | None
    monthly_budget_usd: float | None
    budget_warning_percent: int
    budget_hard_limit_percent: int
    request_log_retention_days: int | None
    analytics_retention_days: int | None
    audit_log_retention_days: int | None
    cost_disclaimer: str = "Budgets and costs are based on estimated data, not exact provider billing."

    model_config = {"from_attributes": True}


class OrganizationSettingsUpdate(BaseModel):
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=100000)
    rate_limit_per_day: int | None = Field(default=None, ge=1, le=10000000)
    monthly_token_limit: int | None = Field(default=None, ge=0)
    monthly_budget_usd: float | None = Field(default=None, ge=0)
    budget_warning_percent: int | None = Field(default=None, ge=1, le=100)
    budget_hard_limit_percent: int | None = Field(default=None, ge=1, le=100)
    request_log_retention_days: int | None = Field(default=None, ge=1, le=3650)
    analytics_retention_days: int | None = Field(default=None, ge=1, le=3650)
    audit_log_retention_days: int | None = Field(default=None, ge=1, le=3650)


class BudgetAlertResponse(BaseModel):
    id: uuid.UUID
    alert_type: str
    threshold_percent: int
    estimated_spend_usd: float
    budget_usd: float
    message: str
    acknowledged: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class JobRunResponse(BaseModel):
    id: uuid.UUID
    job_name: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    duration_ms: float | None
    records_processed: int | None
    error_message: str | None

    model_config = {"from_attributes": True}
