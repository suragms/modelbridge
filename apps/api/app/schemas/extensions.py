"""Pydantic schemas for extensions and templates."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PackageVersionResponse(BaseModel):
    id: uuid.UUID
    version: str
    compatibility_version: str
    permissions: list[str]
    configuration_schema: dict | None
    published_at: datetime

    model_config = {"from_attributes": True}


class PackageResponse(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str
    description: str | None
    plugin_type: str
    trust_level: str
    category: str | None
    publisher_name: str | None = None
    versions: list[PackageVersionResponse] = []

    model_config = {"from_attributes": True}


class InstallationResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    status: str
    health_status: str
    last_error: str | None
    failure_count: int
    execution_count: int
    avg_latency_ms: float | None
    installed_at: datetime
    enabled_at: datetime | None
    package_name: str | None = None
    package_display_name: str | None = None
    plugin_type: str | None = None
    version: str | None = None
    permissions: list[str] = []
    trust_level: str | None = None

    model_config = {"from_attributes": True}


class InstallRequest(BaseModel):
    package_version_id: uuid.UUID
    approved_permissions: list[str]
    config: dict = Field(default_factory=dict)
    secrets: dict | None = None
    enable: bool = False


class UpdateConfigRequest(BaseModel):
    config: dict = Field(default_factory=dict)
    secrets: dict | None = None


class PublishRequest(BaseModel):
    manifest: dict
    publisher_slug: str
    publisher_name: str
    trust_level: str = "community"
    category: str | None = None


class RegistryCreateRequest(BaseModel):
    name: str
    registry_type: str = "private"
    base_url: str | None = None
    auth_token: str | None = None


class TemplateInstallRequest(BaseModel):
    parameters: dict = Field(default_factory=dict)
    activate: bool = False


class SearchParams(BaseModel):
    q: str | None = None
    plugin_type: str | None = None
    trust_level: str | None = None
    category: str | None = None
