"""Marketplace API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MarketplaceItemCreate(BaseModel):
    manifest: dict
    publisher_slug: str = Field(min_length=2, max_length=100)
    publisher_name: str = Field(min_length=1, max_length=255)
    visibility: str = "public"


class MarketplaceVersionCreate(BaseModel):
    manifest: dict


class MarketplaceInstallRequest(BaseModel):
    approved_permissions: list[str] = Field(default_factory=list)
    version_id: uuid.UUID | None = None
    enable: bool = True
    config: dict = Field(default_factory=dict)


class MarketplaceReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    title: str | None = None
    body: str | None = None


class MarketplaceReportCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=80)
    details: str | None = None


class PublisherCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    website: str | None = None


class PublisherResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    website: str | None
    verification_status: str
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MarketplaceVersionResponse(BaseModel):
    id: uuid.UUID
    version: str
    compatibility_version: str
    permissions: list[str]
    changelog: str | None
    published_at: datetime
    security_review_status: str | None = None

    model_config = {"from_attributes": True}


class MarketplaceItemResponse(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    description: str | None
    content_type: str
    category: str | None
    status: str
    visibility: str
    featured: bool
    install_count: int
    view_count: int
    security_review_status: str
    publisher_slug: str | None = None
    publisher_name: str | None = None
    publisher_verification: str | None = None
    trust_level: str | None = None
    documentation_url: str | None = None
    current_version: MarketplaceVersionResponse | None = None
    versions: list[MarketplaceVersionResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None


class MarketplaceDiscoveryResponse(BaseModel):
    featured: list[MarketplaceItemResponse]
    official: list[MarketplaceItemResponse]
    recent: list[MarketplaceItemResponse]
    popular: list[MarketplaceItemResponse]
    categories: list[str]


class MarketplaceSubmissionResponse(BaseModel):
    id: uuid.UUID
    item_id: uuid.UUID
    status: str
    validation_errors: list[str]
    security_review_status: str
    created_at: datetime
    reviewed_at: datetime | None = None

    model_config = {"from_attributes": True}


class MarketplaceInstallHistoryResponse(BaseModel):
    id: uuid.UUID
    item_id: uuid.UUID
    version_id: uuid.UUID
    action: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
