"""Cloud architecture models: regions, metering, quotas, incidents, rollouts."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RegionStatus(enum.StrEnum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    DISABLED = "disabled"


class DataResidencyPolicy(enum.StrEnum):
    GLOBAL = "global"
    EU_ONLY = "eu_only"
    US_ONLY = "us_only"
    INDIA_ONLY = "india_only"


class InstanceLifecycleStatus(enum.StrEnum):
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    UPDATING = "updating"
    DEGRADED = "degraded"
    FAILED = "failed"
    DECOMMISSIONED = "decommissioned"


class PlaneType(enum.StrEnum):
    CONTROL = "control"
    DATA = "data"
    UNIFIED = "unified"


class IncidentSeverity(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(enum.StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"


class UsageEventType(enum.StrEnum):
    REQUEST = "request"
    TOKENS = "tokens"
    PROVIDER_USAGE = "provider_usage"
    AGENT_EXECUTION = "agent_execution"
    WORKFLOW_EXECUTION = "workflow_execution"


class QuotaResource(enum.StrEnum):
    REQUESTS = "requests"
    TOKENS = "tokens"
    CONCURRENT_EXECUTIONS = "concurrent_executions"
    AGENT_EXECUTIONS = "agent_executions"


class QuotaPeriod(enum.StrEnum):
    HOURLY = "hourly"
    DAILY = "daily"
    MONTHLY = "monthly"


class ConfigScope(enum.StrEnum):
    GLOBAL = "global"
    ORGANIZATION = "organization"
    WORKSPACE = "workspace"
    PROJECT = "project"
    ENVIRONMENT = "environment"


class RolloutStatus(enum.StrEnum):
    PENDING = "pending"
    DEPLOYING = "deploying"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class ServiceHealth(enum.StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class Region(Base):
    __tablename__ = "regions"
    __table_args__ = (UniqueConstraint("code", name="uq_region_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    location: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default=RegionStatus.ACTIVE, index=True)
    capabilities: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    data_residency_zones: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    service_registrations = relationship("ServiceRegistration", back_populates="region", lazy="selectin")


class CloudIncident(Base):
    __tablename__ = "cloud_incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    region_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("regions.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default=IncidentSeverity.MEDIUM, index=True)
    status: Mapped[str] = mapped_column(String(20), default=IncidentStatus.OPEN, index=True)
    affected_service: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class UsageMeterEvent(Base):
    __tablename__ = "usage_meter_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), index=True)
    environment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("environments.id"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    safe_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )


class Quota(Base):
    __tablename__ = "quotas"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "resource",
            "period",
            name="uq_org_quota_resource_period",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    resource: Mapped[str] = mapped_column(String(40), nullable=False)
    period: Mapped[str] = mapped_column(String(20), default=QuotaPeriod.DAILY)
    limit_value: Mapped[float] = mapped_column(Float, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class ScopedConfiguration(Base):
    __tablename__ = "scoped_configurations"
    __table_args__ = (
        UniqueConstraint("scope", "scope_ref_id", "version", name="uq_scoped_config_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    scope: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    scope_ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    change_summary: Mapped[str | None] = mapped_column(Text)
    author_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ConfigurationRollout(Base):
    __tablename__ = "configuration_rollouts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    scoped_configuration_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scoped_configurations.id")
    )
    configuration_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("configuration_versions.id")
    )
    region_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("regions.id"), index=True)
    configuration_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=RolloutStatus.PENDING, index=True)
    deployed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ServiceRegistration(Base):
    __tablename__ = "service_registrations"
    __table_args__ = (UniqueConstraint("service_name", "region_id", name="uq_service_region"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("regions.id"), index=True, nullable=False
    )
    endpoint: Mapped[str] = mapped_column(String(512), nullable=False)
    plane_type: Mapped[str] = mapped_column(String(20), default=PlaneType.DATA)
    health_status: Mapped[str] = mapped_column(String(20), default=ServiceHealth.UNKNOWN, index=True)
    capabilities: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    region = relationship("Region", back_populates="service_registrations")


class FailoverEvent(Base):
    __tablename__ = "failover_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    region_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("regions.id"), index=True)
    source_service: Mapped[str] = mapped_column(String(100), nullable=False)
    target_service: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    safe_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )


class CloudOnboarding(Base):
    __tablename__ = "cloud_onboarding"
    __table_args__ = (UniqueConstraint("organization_id", name="uq_cloud_onboarding_org"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    selected_region_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("regions.id"))
    data_residency_policy: Mapped[str] = mapped_column(String(20), default=DataResidencyPolicy.GLOBAL)
    steps_completed: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
