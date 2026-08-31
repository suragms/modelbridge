"""Cloud platform API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RegionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=64)
    location: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    data_residency_zones: list[str] = Field(default_factory=list)


class RegionUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    status: str | None = None
    capabilities: list[str] | None = None
    data_residency_zones: list[str] | None = None


class RegionResponse(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    location: str | None
    status: str
    capabilities: list[str]
    data_residency_zones: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CloudInstanceResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    endpoint: str
    environment_kind: str | None
    status: str
    lifecycle_status: str
    plane_type: str
    region_id: uuid.UUID | None
    version: str | None
    capabilities: list[str]
    last_seen_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CloudInstanceProvisionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    endpoint: str = Field(..., min_length=1, max_length=512)
    region_id: uuid.UUID | None = None
    plane_type: str = "data"
    environment_kind: str | None = None


class CloudInstanceProvisionResponse(BaseModel):
    instance: CloudInstanceResponse
    credential: str


class InstanceLifecycleRequest(BaseModel):
    target_status: str


class CloudHealthResponse(BaseModel):
    status: str
    deployment_region: str
    plane_type: str
    regions: list[dict]
    providers: dict
    open_incidents: int
    note: str | None = None


class IncidentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    severity: str = "medium"
    description: str | None = None
    region_id: uuid.UUID | None = None
    affected_service: str | None = None


class IncidentUpdate(BaseModel):
    status: str


class IncidentResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID | None
    region_id: uuid.UUID | None
    title: str
    description: str | None
    severity: str
    status: str
    affected_service: str | None
    started_at: datetime
    resolved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UsageSummaryResponse(BaseModel):
    organization_id: str
    period_start: str
    period_end: str
    totals: dict[str, float]
    requests: float
    tokens: float
    agent_executions: float
    workflow_executions: float


class QuotaUpsert(BaseModel):
    resource: str
    period: str = "daily"
    limit_value: float = Field(..., gt=0)
    is_enabled: bool = True


class QuotaResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    resource: str
    period: str
    limit_value: float
    is_enabled: bool
    current_usage: float | None = None
    allowed: bool | None = None

    model_config = {"from_attributes": True}


class ScopedConfigCreate(BaseModel):
    scope: str
    scope_ref_id: uuid.UUID | None = None
    config: dict = Field(default_factory=dict)
    change_summary: str | None = None
    activate: bool = False


class ScopedConfigResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID | None
    scope: str
    scope_ref_id: uuid.UUID | None
    version: int
    config: dict
    is_active: bool
    change_summary: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RolloutResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID | None
    region_id: uuid.UUID | None
    configuration_version: int
    status: str
    verified_at: datetime | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class OnboardingResponse(BaseModel):
    organization_id: uuid.UUID
    selected_region_id: uuid.UUID | None
    data_residency_policy: str
    steps_completed: list[str]
    is_complete: bool
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class OnboardingStepRequest(BaseModel):
    step: str
    selected_region_id: uuid.UUID | None = None
    data_residency_policy: str | None = None


class OnboardingBootstrapRequest(BaseModel):
    workspace_name: str = "Default Workspace"
    project_name: str = "Default Project"
