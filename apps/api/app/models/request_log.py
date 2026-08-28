from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Request lifecycle statuses
REQUEST_STATUS_PENDING = "PENDING"
REQUEST_STATUS_ROUTING = "ROUTING"
REQUEST_STATUS_PROCESSING = "PROCESSING"
REQUEST_STATUS_COMPLETED = "COMPLETED"
REQUEST_STATUS_FAILED = "FAILED"
REQUEST_STATUS_CANCELLED = "CANCELLED"

# Legacy status aliases for backward-compatible queries
SUCCESS_STATUSES = frozenset({REQUEST_STATUS_COMPLETED, "success"})
FAILED_STATUSES = frozenset({REQUEST_STATUS_FAILED, "error"})

# Usage source labels
USAGE_SOURCE_PROVIDER = "PROVIDER_REPORTED"
USAGE_SOURCE_ESTIMATED = "ESTIMATED"
USAGE_SOURCE_UNAVAILABLE = "UNAVAILABLE"

# Pricing source labels
PRICING_SOURCE_PROVIDER = "PROVIDER_PRICING"
PRICING_SOURCE_MANUAL = "MANUAL_PRICING"
PRICING_SOURCE_CUSTOM = "CUSTOM_PRICING"
PRICING_SOURCE_UNKNOWN = "UNKNOWN"


class RequestLog(Base):
    __tablename__ = "request_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    error: Mapped[str | None] = mapped_column(Text)
    routing_strategy: Mapped[str | None] = mapped_column(String(50))
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)

    requested_model: Mapped[str | None] = mapped_column(String(255))
    selected_model: Mapped[str | None] = mapped_column(String(255))
    routing_policy: Mapped[str | None] = mapped_column(String(255))
    candidates_count: Mapped[int | None] = mapped_column(Integer)
    fallback_count: Mapped[int | None] = mapped_column(Integer)

    provider_latency_ms: Mapped[float | None] = mapped_column(Float)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(50))
    error_type: Mapped[str | None] = mapped_column(String(50))
    request_type: Mapped[str] = mapped_column(String(30), default="chat")
    required_capabilities: Mapped[str | None] = mapped_column(String(255))
    input_count: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_keys.id")
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(255), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    usage_source: Mapped[str] = mapped_column(String(30), default=USAGE_SOURCE_UNAVAILABLE)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id")
    )


class CostRecord(Base):
    __tablename__ = "cost_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(255), nullable=False)
    input_cost: Mapped[float] = mapped_column(Float, default=0.0)
    output_cost: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    is_estimated: Mapped[bool] = mapped_column(default=True)
    pricing_source: Mapped[str] = mapped_column(String(30), default=PRICING_SOURCE_UNKNOWN)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id")
    )
