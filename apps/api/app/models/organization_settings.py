from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrganizationSettings(Base):
    __tablename__ = "organization_settings"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), primary_key=True
    )
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=100)
    rate_limit_per_day: Mapped[int] = mapped_column(Integer, default=10000)
    monthly_token_limit: Mapped[int | None] = mapped_column(BigInteger)
    monthly_budget_usd: Mapped[float | None] = mapped_column(Float)
    budget_warning_percent: Mapped[int] = mapped_column(Integer, default=80)
    budget_hard_limit_percent: Mapped[int] = mapped_column(Integer, default=100)
    request_log_retention_days: Mapped[int | None] = mapped_column(Integer)
    analytics_retention_days: Mapped[int | None] = mapped_column(Integer)
    audit_log_retention_days: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    organization = relationship("Organization", back_populates="settings", lazy="selectin")
