"""Developer platform API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EventCatalogEntry(BaseModel):
    type: str
    description: str
    category: str


class PlatformEventResponse(BaseModel):
    id: uuid.UUID
    type: str
    organization_id: uuid.UUID
    timestamp: datetime
    schema_version: str
    data: dict
    source: str

    model_config = {"from_attributes": True}


class WebhookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=8, max_length=2048)
    event_types: list[str] = Field(min_length=1)


class WebhookUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    event_types: list[str] | None = None
    status: str | None = None


class WebhookResponse(BaseModel):
    id: uuid.UUID
    name: str
    url: str
    event_types: list[str]
    status: str
    secret_prefix: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WebhookCreated(WebhookResponse):
    secret: str


class WebhookDeliveryResponse(BaseModel):
    id: uuid.UUID
    webhook_id: uuid.UUID
    event_id: uuid.UUID
    status: str
    attempt_count: int
    max_attempts: int
    last_attempt_at: datetime | None
    next_retry_at: datetime | None
    response_status: int | None
    failure_category: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class IntegrationCreate(BaseModel):
    provider: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=255)
    config: dict = Field(default_factory=dict)


class IntegrationConnect(BaseModel):
    credential: str = Field(min_length=1)
    webhook_secret: str | None = None


class IntegrationUpdate(BaseModel):
    name: str | None = None
    config: dict | None = None
    status: str | None = None


class IntegrationResponse(BaseModel):
    id: uuid.UUID
    provider: str
    name: str
    status: str
    config: dict
    last_sync_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AutomationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    trigger_type: str
    trigger_config: dict = Field(default_factory=dict)
    action_type: str
    action_config: dict = Field(default_factory=dict)
    template_id: str | None = None
    requires_approval: bool = False


class AutomationUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    trigger_config: dict | None = None
    action_config: dict | None = None
    status: str | None = None
    requires_approval: bool | None = None


class AutomationResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    trigger_type: str
    trigger_config: dict
    action_type: str
    action_config: dict
    template_id: str | None
    status: str
    requires_approval: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AutomationTemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    trigger_type: str
    trigger_config: dict
    action_type: str


class AutomationExecutionResponse(BaseModel):
    id: uuid.UUID
    automation_id: uuid.UUID
    event_id: uuid.UUID | None
    status: str
    trigger_summary: str | None
    result_summary: dict | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AutomationExecuteRequest(BaseModel):
    force: bool = False
    context: dict = Field(default_factory=dict)


class DeveloperActivityEntry(BaseModel):
    event_type: str
    resource_type: str | None
    resource_id: str | None
    timestamp: datetime
    metadata: dict = Field(default_factory=dict)
