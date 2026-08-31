"""Extension ecosystem persistence models."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PluginType(enum.StrEnum):
    PROVIDER = "provider"
    TOOL = "tool"
    INTEGRATION = "integration"
    AGENT_TEMPLATE = "agent_template"
    WORKFLOW_TEMPLATE = "workflow_template"


class TrustLevel(enum.StrEnum):
    OFFICIAL = "official"
    VERIFIED = "verified"
    COMMUNITY = "community"
    UNVERIFIED = "unverified"


class InstallationStatus(enum.StrEnum):
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    UNINSTALLED = "uninstalled"


class ExtensionRegistry(Base):
    """Private or organization registry configuration."""

    __tablename__ = "extension_registries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    registry_type: Mapped[str] = mapped_column(String(30), default="local", nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(512))
    encrypted_auth: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ExtensionPublisher(Base):
    __tablename__ = "extension_publishers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    homepage: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(20), default="active")
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ExtensionPackage(Base):
    __tablename__ = "extension_packages"
    __table_args__ = (UniqueConstraint("registry_id", "name", name="uq_package_registry_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extension_registries.id"), index=True
    )
    publisher_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extension_publishers.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    plugin_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    trust_level: Mapped[str] = mapped_column(String(20), default=TrustLevel.UNVERIFIED, index=True)
    category: Mapped[str | None] = mapped_column(String(50), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    publisher = relationship("ExtensionPublisher", lazy="selectin")
    versions = relationship(
        "ExtensionPackageVersion",
        back_populates="package",
        lazy="selectin",
        order_by="ExtensionPackageVersion.published_at.desc()",
    )


class ExtensionPackageVersion(Base):
    __tablename__ = "extension_package_versions"
    __table_args__ = (UniqueConstraint("package_id", "version", name="uq_package_version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extension_packages.id"), index=True, nullable=False
    )
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    compatibility_version: Mapped[str] = mapped_column(String(40), default="1.0.0")
    manifest: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    permissions: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    configuration_schema: Mapped[dict | None] = mapped_column(JSONB)
    entry_point: Mapped[str | None] = mapped_column(String(255))
    template_definition: Mapped[dict | None] = mapped_column(JSONB)
    changelog: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    published_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    package = relationship("ExtensionPackage", back_populates="versions")


class ExtensionInstallation(Base):
    __tablename__ = "extension_installations"
    __table_args__ = (
        UniqueConstraint("organization_id", "package_version_id", name="uq_org_package_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    package_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extension_package_versions.id"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default=InstallationStatus.INSTALLED, index=True)
    previous_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extension_package_versions.id")
    )
    installed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    enabled_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    last_error: Mapped[str | None] = mapped_column(Text)
    health_status: Mapped[str] = mapped_column(String(20), default="unknown")
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    execution_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_latency_ms: Mapped[float | None] = mapped_column(Float)
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    package_version = relationship("ExtensionPackageVersion", foreign_keys=[package_version_id], lazy="selectin")
    configuration = relationship(
        "ExtensionConfiguration",
        back_populates="installation",
        uselist=False,
        lazy="selectin",
    )


class ExtensionConfiguration(Base):
    __tablename__ = "extension_configurations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("extension_installations.id"), unique=True, nullable=False
    )
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    encrypted_secrets: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    installation = relationship("ExtensionInstallation", back_populates="configuration")
