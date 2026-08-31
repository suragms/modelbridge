from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Default scopes when none specified (backward compatible full gateway access).
DEFAULT_API_KEY_SCOPES = [
    "chat:write",
    "embeddings:write",
    "models:read",
    "analytics:read",
    "providers:read",
]

PLATFORM_API_KEY_SCOPES = [
    "requests:read",
    "requests:write",
    "workflows:read",
    "workflows:execute",
    "webhooks:manage",
    "integrations:manage",
    "automations:manage",
    "events:read",
]

ALL_API_KEY_SCOPES = frozenset(DEFAULT_API_KEY_SCOPES + PLATFORM_API_KEY_SCOPES)


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    scopes: Mapped[list] = mapped_column(JSONB, default=list)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    monthly_token_limit: Mapped[int | None] = mapped_column(BigInteger)
    monthly_budget_usd: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_ip: Mapped[str | None] = mapped_column(String(45))
    rotated_from_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id")
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )

    user = relationship("User", back_populates="api_keys", foreign_keys=[user_id], lazy="selectin")
    organization = relationship("Organization", back_populates="api_keys", lazy="selectin")
    created_by = relationship("User", foreign_keys=[created_by_id], lazy="selectin")

    def effective_scopes(self) -> list[str]:
        if self.scopes:
            return list(self.scopes)
        return list(DEFAULT_API_KEY_SCOPES)

    def has_scope(self, scope: str) -> bool:
        return scope in self.effective_scopes()
