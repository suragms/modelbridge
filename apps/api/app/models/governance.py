"""Governance persistence: policies, versions, events, approvals, settings."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PolicyStatus(enum.StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DRAFT = "draft"


class PolicyType(enum.StrEnum):
    ORGANIZATION = "organization"
    MODEL = "model"
    PROVIDER = "provider"
    API_KEY = "api_key"
    REQUEST = "request"
    RESPONSE = "response"


class PolicyAction(enum.StrEnum):
    ALLOW = "allow"
    WARN = "warn"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    REDACT = "redact"


class ApprovalStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class GovernancePolicy(Base):
    __tablename__ = "governance_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    policy_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=PolicyStatus.DRAFT, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    rules: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    action: Mapped[str] = mapped_column(String(40), default=PolicyAction.DENY, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    versions = relationship(
        "PolicyVersion",
        back_populates="policy",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="PolicyVersion.version.desc()",
    )


class PolicyVersion(Base):
    __tablename__ = "governance_policy_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("governance_policies.id"), index=True, nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    rules: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    policy = relationship("GovernancePolicy", back_populates="versions")


class GovernanceEvent(Base):
    __tablename__ = "governance_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    decision: Mapped[str | None] = mapped_column(String(40))
    policy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("governance_policies.id"))
    policy_name: Mapped[str | None] = mapped_column(String(255))
    policy_type: Mapped[str | None] = mapped_column(String(50))
    reason: Mapped[str | None] = mapped_column(Text)
    risk_level: Mapped[str | None] = mapped_column(String(20), index=True)
    classification: Mapped[str | None] = mapped_column(String(40))
    detection_categories: Mapped[list | None] = mapped_column(JSONB)
    requested_model: Mapped[str | None] = mapped_column(String(255))
    request_id: Mapped[str | None] = mapped_column(String(64), index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )


class ApprovalRequest(Base):
    __tablename__ = "governance_approvals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default=ApprovalStatus.PENDING, index=True)
    request_type: Mapped[str] = mapped_column(String(40), default="chat")
    risk_level: Mapped[str | None] = mapped_column(String(20))
    classification: Mapped[str | None] = mapped_column(String(40))
    matched_policy_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("governance_policies.id"))
    matched_policy_name: Mapped[str | None] = mapped_column(String(255))
    requested_model: Mapped[str | None] = mapped_column(String(255))
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    requester_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    review_comment: Mapped[str | None] = mapped_column(Text)
    safe_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GovernanceNotification(Base):
    __tablename__ = "governance_notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="info")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("governance_events.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)


class GovernanceSettings(Base):
    __tablename__ = "governance_settings"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), primary_key=True
    )
    pii_detection_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    secret_detection_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    redact_prompts: Mapped[bool] = mapped_column(Boolean, default=False)
    redact_responses: Mapped[bool] = mapped_column(Boolean, default=False)
    block_on_secret: Mapped[bool] = mapped_column(Boolean, default=True)
    block_sensitive_to_cloud: Mapped[bool] = mapped_column(Boolean, default=False)
    require_local_for_high_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_cloud_providers: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_local_providers: Mapped[bool] = mapped_column(Boolean, default=True)
    content_safety_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    approval_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    approval_ttl_hours: Mapped[int] = mapped_column(Integer, default=24)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
