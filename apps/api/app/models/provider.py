from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProviderType(enum.StrEnum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    GROQ = "groq"
    OPENROUTER = "openrouter"
    LMSTUDIO = "lmstudio"
    CUSTOM = "custom"


class ProviderStatus(enum.StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[ProviderType] = mapped_column(String(50), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[ProviderStatus] = mapped_column(
        String(20), default=ProviderStatus.UNKNOWN
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # Health monitoring state (updated by HealthService).
    last_health_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_health_latency_ms: Mapped[float | None] = mapped_column(Float)
    total_health_checks: Mapped[int] = mapped_column(Integer, default=0)
    failed_health_checks: Mapped[int] = mapped_column(Integer, default=0)
    region: Mapped[str | None] = mapped_column(String(64))
    data_residency: Mapped[str | None] = mapped_column(String(64))
    deployment_type: Mapped[str | None] = mapped_column(String(20))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id")
    )

    organization = relationship("Organization", back_populates="providers", lazy="selectin")
    credentials = relationship("ProviderCredential", back_populates="provider", lazy="selectin")
    models = relationship("Model", back_populates="provider", lazy="selectin")
    health_checks = relationship("HealthCheck", back_populates="provider", lazy="selectin")


class ProviderCredential(Base):
    __tablename__ = "provider_credentials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    key_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id")
    )
    provider = relationship("Provider", back_populates="credentials", lazy="selectin")
