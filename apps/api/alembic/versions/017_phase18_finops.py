"""Phase 18 AI FinOps tables.

Revision ID: 017_phase18_finops
Revises: 016_phase17_quality
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "017_phase18_finops"
down_revision = "016_phase17_quality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "finops_provider_pricing",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("input_price_per_million", sa.Float(), server_default="0"),
        sa.Column("output_price_per_million", sa.Float(), server_default="0"),
        sa.Column("currency", sa.String(10), server_default="USD"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_finops_pricing_org", "finops_provider_pricing", ["organization_id"])

    op.create_table(
        "finops_cost_attributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id")),
        sa.Column("environment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("environments.id")),
        sa.Column("team", sa.String(100)),
        sa.Column("application", sa.String(100)),
        sa.Column("tags", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_finops_attr_org", "finops_cost_attributions", ["organization_id"])
    op.create_index("ix_finops_attr_req", "finops_cost_attributions", ["request_id"])

    op.create_table(
        "finops_budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("scope", sa.String(30), server_default="organization"),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True)),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(10), server_default="USD"),
        sa.Column("period", sa.String(20), server_default="monthly"),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True)),
        sa.Column("thresholds", postgresql.JSONB(), server_default="[50, 75, 90, 100]", nullable=False),
        sa.Column("enforcement_action", sa.String(30), server_default="alert"),
        sa.Column("enabled", sa.Boolean(), server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "finops_budget_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("budget_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("finops_budgets.id"), nullable=False),
        sa.Column("threshold_percent", sa.Integer(), nullable=False),
        sa.Column("current_spend", sa.Float(), nullable=False),
        sa.Column("budget_amount", sa.Float(), nullable=False),
        sa.Column("cost_type", sa.String(20), server_default="estimated"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "finops_cost_anomalies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("anomaly_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("affected_scope", sa.String(100), nullable=False),
        sa.Column("expected_range", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("observed_value", sa.Float(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "finops_cost_forecasts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("scope", sa.String(30), server_default="organization"),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True)),
        sa.Column("method", sa.String(50), nullable=False),
        sa.Column("historical_period_days", sa.Integer(), server_default="30"),
        sa.Column("forecast_amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(10), server_default="USD"),
        sa.Column("cost_type", sa.String(20), server_default="estimated"),
        sa.Column("confidence", sa.String(20)),
        sa.Column("limitations", sa.Text(), nullable=False),
        sa.Column("data_points", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "finops_optimization_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("projected_savings", sa.Float()),
        sa.Column("savings_status", sa.String(20), server_default="projected"),
        sa.Column("assumptions", sa.Text(), nullable=False),
        sa.Column("confidence", sa.String(20)),
        sa.Column("risk", sa.String(20)),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "finops_savings_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("finops_optimization_recommendations.id")),
        sa.Column("status", sa.String(20), server_default="projected"),
        sa.Column("projected_amount", sa.Float()),
        sa.Column("measured_amount", sa.Float()),
        sa.Column("currency", sa.String(10), server_default="USD"),
        sa.Column("period_start", sa.DateTime(timezone=True)),
        sa.Column("period_end", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "finops_chargeback_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("report_type", sa.String(20), server_default="showback"),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cost_center", sa.String(100)),
        sa.Column("department", sa.String(100)),
        sa.Column("project_id", postgresql.UUID(as_uuid=True)),
        sa.Column("total_cost", sa.Float(), server_default="0"),
        sa.Column("cost_type", sa.String(20), server_default="estimated"),
        sa.Column("breakdown", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("generated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "finops_cost_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("period_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dimension", sa.String(30), nullable=False),
        sa.Column("dimension_key", sa.String(255), nullable=False),
        sa.Column("total_cost", sa.Float(), server_default="0"),
        sa.Column("request_count", sa.Integer(), server_default="0"),
        sa.Column("input_tokens", sa.Integer(), server_default="0"),
        sa.Column("output_tokens", sa.Integer(), server_default="0"),
        sa.Column("cost_type", sa.String(20), server_default="estimated"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "period_date", "dimension", "dimension_key", name="uq_finops_snapshot"),
    )

    op.create_table(
        "finops_governance_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("scope", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("details", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    for table in (
        "finops_governance_audits",
        "finops_cost_snapshots",
        "finops_chargeback_reports",
        "finops_savings_records",
        "finops_optimization_recommendations",
        "finops_cost_forecasts",
        "finops_cost_anomalies",
        "finops_budget_events",
        "finops_budgets",
        "finops_cost_attributions",
        "finops_provider_pricing",
    ):
        op.drop_table(table)
