"""Enterprise collaboration and fleet control-plane models."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WorkspaceStatus(enum.StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class WorkspaceRole(enum.StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class ProjectStatus(enum.StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ProjectRole(enum.StrEnum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class EnvironmentKind(enum.StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    CUSTOM = "custom"


class InstanceStatus(enum.StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


class DeploymentStatus(enum.StrEnum):
    PENDING = "pending"
    DEPLOYING = "deploying"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class SyncStatus(enum.StrEnum):
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"
    OUT_OF_DATE = "out_of_date"


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=WorkspaceStatus.ACTIVE, index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    members = relationship("WorkspaceMember", back_populates="workspace", lazy="selectin")
    projects = relationship("Project", back_populates="workspace", lazy="selectin")


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), default=WorkspaceRole.MEMBER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    workspace = relationship("Workspace", back_populates="members")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=ProjectStatus.ACTIVE, index=True)
    is_restricted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    workspace = relationship("Workspace", back_populates="projects")
    members = relationship("ProjectMember", back_populates="project", lazy="selectin")
    environments = relationship("Environment", back_populates="project", lazy="selectin")


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), default=ProjectRole.MEMBER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    project = relationship("Project", back_populates="members")


class Environment(Base):
    __tablename__ = "environments"
    __table_args__ = (UniqueConstraint("project_id", "slug", name="uq_project_env_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default=EnvironmentKind.CUSTOM)
    is_protected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    project = relationship("Project", back_populates="environments")
    configuration_versions = relationship(
        "ConfigurationVersion",
        back_populates="environment",
        lazy="selectin",
        order_by="ConfigurationVersion.version.desc()",
    )


class ConfigurationVersion(Base):
    __tablename__ = "configuration_versions"
    __table_args__ = (UniqueConstraint("environment_id", "version", name="uq_env_config_version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    environment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("environments.id"), index=True, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    secret_refs: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text)
    author_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    environment = relationship("Environment", back_populates="configuration_versions")


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(50))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    safe_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )


class ManagedInstance(Base):
    __tablename__ = "managed_instances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(512), nullable=False)
    environment_kind: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default=InstanceStatus.OFFLINE, index=True)
    version: Mapped[str | None] = mapped_column(String(40))
    capabilities: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    credential_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    region_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("regions.id"), index=True)
    lifecycle_status: Mapped[str] = mapped_column(String(20), default="provisioning", index=True)
    plane_type: Mapped[str] = mapped_column(String(20), default="data")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    registered_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    heartbeats = relationship(
        "InstanceHeartbeat",
        back_populates="instance",
        lazy="selectin",
        order_by="InstanceHeartbeat.created_at.desc()",
    )
    policy_syncs = relationship("PolicySyncRecord", back_populates="instance", lazy="selectin")


class InstanceHeartbeat(Base):
    __tablename__ = "instance_heartbeats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("managed_instances.id"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    version: Mapped[str | None] = mapped_column(String(40))
    capabilities: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    metrics_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )

    instance = relationship("ManagedInstance", back_populates="heartbeats")


class ConfigurationDeployment(Base):
    __tablename__ = "configuration_deployments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    environment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("environments.id"))
    instance_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("managed_instances.id"))
    configuration_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("configuration_versions.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default=DeploymentStatus.PENDING, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), index=True)
    deployed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PolicySyncRecord(Base):
    __tablename__ = "policy_sync_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("managed_instances.id"), index=True, nullable=False
    )
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False)
    instance_policy_version: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=SyncStatus.PENDING)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    instance = relationship("ManagedInstance", back_populates="policy_syncs")
