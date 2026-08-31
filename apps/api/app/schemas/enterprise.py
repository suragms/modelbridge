"""Enterprise API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str
    description: str | None = None


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None


class WorkspaceMemberAdd(BaseModel):
    user_id: uuid.UUID
    role: str = "member"


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: str | None
    status: str
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    project_count: int = 0
    member_count: int = 0

    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    workspace_id: uuid.UUID
    name: str
    description: str | None = None
    is_restricted: bool = False


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    is_restricted: bool | None = None


class ProjectMemberAdd(BaseModel):
    user_id: uuid.UUID
    role: str = "member"


class ProjectResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    status: str
    is_restricted: bool
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EnvironmentResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    slug: str
    kind: str
    is_protected: bool
    active_config_version: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConfigVersionCreate(BaseModel):
    config: dict = Field(default_factory=dict)
    secret_refs: dict = Field(default_factory=dict)
    change_summary: str | None = None
    activate: bool = False


class ConfigVersionResponse(BaseModel):
    id: uuid.UUID
    environment_id: uuid.UUID
    version: int
    config: dict
    secret_refs: dict
    change_summary: str | None
    is_active: bool
    author_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PromoteRequest(BaseModel):
    target_environment_id: uuid.UUID
    require_approval: bool = True


class CompareRequest(BaseModel):
    version_a_id: uuid.UUID
    version_b_id: uuid.UUID


class InstanceRegisterRequest(BaseModel):
    name: str
    endpoint: str
    environment_kind: str | None = None


class InstanceRegisterResponse(BaseModel):
    id: uuid.UUID
    name: str
    endpoint: str
    credential: str
    status: str


class InstanceResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    endpoint: str
    environment_kind: str | None
    status: str
    version: str | None
    capabilities: list
    last_seen_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class HeartbeatRequest(BaseModel):
    status: str
    version: str | None = None
    capabilities: list = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)


class DeploymentResponse(BaseModel):
    id: uuid.UUID
    status: str
    configuration_version_id: uuid.UUID
    verified_at: datetime | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    resource_type: str | None
    resource_id: str | None
    actor_id: uuid.UUID | None
    safe_metadata: dict | None = Field(None, validation_alias="metadata")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class EnterpriseOverviewResponse(BaseModel):
    workspaces: int
    projects: int
    environments: int
    instances: int
    healthy_instances: int
    recent_deployments: int
    pending_policy_syncs: int
