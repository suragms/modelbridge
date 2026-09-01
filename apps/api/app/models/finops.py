"""AI FinOps & Cost Intelligence persistence."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CostType(enum.StrEnum):
    ACTUAL = "actual"
    ESTIMATED = "estimated"
    CONFIGURED = "configured"
    UNKNOWN = "unknown"


class BudgetScope(enum.StrEnum):
    ORGANIZATION = "organization"
    TEAM = "team"
    PROJECT = "project"
    WORKSPACE = "workspace"
    ENVIRONMENT = "environment"


class BudgetPeriod(enum.StrEnum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class EnforcementAction(enum.StrEnum):
    ALERT = "alert"
    REQUIRE_APPROVAL = "require_approval"
    RESTRICT_REQUESTS = "restrict_requests"


class AnomalyStatus(enum.StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class RecommendationStatus(enum.StrEnum):
    OPEN = "open"
    APPROVED = "approved"
    APPLIED = "applied"
    REJECTED = "rejected"
    VERIFIED = "verified"


class SavingsStatus(enum.StrEnum):
    PROJECTED = "projected"
    MEASURED = "measured"
    UNVERIFIED = "unverified"


ALLOWED_TAG_KEYS = frozenset({"project", "department", "environment", "application", "team", "cost_center"})


class FinopsProviderPricing(Base):
    __tablename__ = "finops_provider_pricing"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    input_price_per_million: Mapped[float] = mapped_column(Float, default=0.0)
    output_price_per_million: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class FinopsCostAttribution(Base):
    __tablename__ = "finops_cost_attributions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    request_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"))
    environment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("environments.id"))
    team: Mapped[str | None] = mapped_column(String(100))
    application: Mapped[str | None] = mapped_column(String(100))
    tags: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class FinopsBudget(Base):
    __tablename__ = "finops_budgets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str] = mapped_column(String(30), default=BudgetScope.ORGANIZATION)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    period: Mapped[str] = mapped_column(String(20), default=BudgetPeriod.MONTHLY)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    thresholds: Mapped[list] = mapped_column(JSONB, default=lambda: [50, 75, 90, 100], nullable=False)
    enforcement_action: Mapped[str] = mapped_column(String(30), default=EnforcementAction.ALERT)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class FinopsBudgetEvent(Base):
    __tablename__ = "finops_budget_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("finops_budgets.id"), index=True, nullable=False
    )
    threshold_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    current_spend: Mapped[float] = mapped_column(Float, nullable=False)
    budget_amount: Mapped[float] = mapped_column(Float, nullable=False)
    cost_type: Mapped[str] = mapped_column(String(20), default=CostType.ESTIMATED)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class FinopsCostAnomaly(Base):
    __tablename__ = "finops_cost_anomalies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    anomaly_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=AnomalyStatus.OPEN)
    affected_scope: Mapped[str] = mapped_column(String(100), nullable=False)
    expected_range: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    observed_value: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FinopsCostForecast(Base):
    __tablename__ = "finops_cost_forecasts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    scope: Mapped[str] = mapped_column(String(30), default=BudgetScope.ORGANIZATION)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    historical_period_days: Mapped[int] = mapped_column(Integer, default=30)
    forecast_amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    cost_type: Mapped[str] = mapped_column(String(20), default=CostType.ESTIMATED)
    confidence: Mapped[str | None] = mapped_column(String(20))
    limitations: Mapped[str] = mapped_column(Text, nullable=False)
    data_points: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class FinopsOptimizationRecommendation(Base):
    __tablename__ = "finops_optimization_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    projected_savings: Mapped[float | None] = mapped_column(Float)
    savings_status: Mapped[str] = mapped_column(String(20), default=SavingsStatus.PROJECTED)
    assumptions: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str | None] = mapped_column(String(20))
    risk: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default=RecommendationStatus.OPEN)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class FinopsSavingsRecord(Base):
    __tablename__ = "finops_savings_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    recommendation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("finops_optimization_recommendations.id")
    )
    status: Mapped[str] = mapped_column(String(20), default=SavingsStatus.PROJECTED)
    projected_amount: Mapped[float | None] = mapped_column(Float)
    measured_amount: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class FinopsChargebackReport(Base):
    __tablename__ = "finops_chargeback_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    report_type: Mapped[str] = mapped_column(String(20), default="showback")
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cost_center: Mapped[str | None] = mapped_column(String(100))
    department: Mapped[str | None] = mapped_column(String(100))
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    cost_type: Mapped[str] = mapped_column(String(20), default=CostType.ESTIMATED)
    breakdown: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class FinopsCostSnapshot(Base):
    __tablename__ = "finops_cost_snapshots"
    __table_args__ = (UniqueConstraint("organization_id", "period_date", "dimension", "dimension_key", name="uq_finops_snapshot"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    period_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dimension: Mapped[str] = mapped_column(String(30), nullable=False)
    dimension_key: Mapped[str] = mapped_column(String(255), nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_type: Mapped[str] = mapped_column(String(20), default=CostType.ESTIMATED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class FinopsGovernanceAudit(Base):
    __tablename__ = "finops_governance_audits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    scope: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
