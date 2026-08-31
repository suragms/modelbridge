"""Phase 13 intelligence layer tables.

Revision ID: 012_phase13_intelligence
Revises: 011_phase12_cloud
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "012_phase13_intelligence"
down_revision = "011_phase12_cloud"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operational_aggregates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("granularity", sa.String(20), server_default="daily"),
        sa.Column("metrics", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("sample_size", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_operational_aggregates_organization_id", "operational_aggregates", ["organization_id"])
    op.create_index("ix_operational_aggregates_period_start", "operational_aggregates", ["period_start"])

    op.create_table(
        "intelligence_forecasts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("forecast_type", sa.String(40), nullable=False),
        sa.Column("historical_window_days", sa.Integer(), nullable=False),
        sa.Column("method", sa.String(40), nullable=False),
        sa.Column("horizon_days", sa.Integer(), server_default="7"),
        sa.Column("forecast_value", sa.Float()),
        sa.Column("confidence", sa.Float(), server_default="0"),
        sa.Column("data_quality", sa.String(30), server_default="unknown"),
        sa.Column("supporting_data", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_intelligence_forecasts_organization_id", "intelligence_forecasts", ["organization_id"])
    op.create_index("ix_intelligence_forecasts_forecast_type", "intelligence_forecasts", ["forecast_type"])

    op.create_table(
        "intelligence_anomalies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("metric", sa.String(60), nullable=False),
        sa.Column("dimension", sa.String(100)),
        sa.Column("observed_value", sa.Float(), nullable=False),
        sa.Column("expected_min", sa.Float()),
        sa.Column("expected_max", sa.Float()),
        sa.Column("deviation", sa.Float()),
        sa.Column("severity", sa.String(20), server_default="medium"),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("evidence", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_intelligence_anomalies_organization_id", "intelligence_anomalies", ["organization_id"])
    op.create_index("ix_intelligence_anomalies_metric", "intelligence_anomalies", ["metric"])
    op.create_index("ix_intelligence_anomalies_severity", "intelligence_anomalies", ["severity"])
    op.create_index("ix_intelligence_anomalies_status", "intelligence_anomalies", ["status"])
    op.create_index("ix_intelligence_anomalies_detected_at", "intelligence_anomalies", ["detected_at"])

    op.create_table(
        "intelligence_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20), server_default="medium"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("suggested_action", sa.Text()),
        sa.Column("confidence", sa.Float(), server_default="0"),
        sa.Column("risks", sa.Text()),
        sa.Column("policy_constraints", postgresql.JSONB()),
        sa.Column("automation_level", sa.String(30), server_default="recommend"),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_intelligence_recommendations_organization_id", "intelligence_recommendations", ["organization_id"])
    op.create_index("ix_intelligence_recommendations_category", "intelligence_recommendations", ["category"])
    op.create_index("ix_intelligence_recommendations_status", "intelligence_recommendations", ["status"])
    op.create_index("ix_intelligence_recommendations_created_at", "intelligence_recommendations", ["created_at"])

    op.create_table(
        "recommendation_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("intelligence_recommendations.id"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("notes", sa.Text()),
        sa.Column("metadata", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_recommendation_actions_recommendation_id", "recommendation_actions", ["recommendation_id"])
    op.create_index("ix_recommendation_actions_organization_id", "recommendation_actions", ["organization_id"])

    op.create_table(
        "intelligence_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("job_type", sa.String(60), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.Float()),
        sa.Column("error_message", sa.Text()),
        sa.Column("result_summary", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_intelligence_jobs_organization_id", "intelligence_jobs", ["organization_id"])
    op.create_index("ix_intelligence_jobs_job_type", "intelligence_jobs", ["job_type"])
    op.create_index("ix_intelligence_jobs_status", "intelligence_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("intelligence_jobs")
    op.drop_table("recommendation_actions")
    op.drop_table("intelligence_recommendations")
    op.drop_table("intelligence_anomalies")
    op.drop_table("intelligence_forecasts")
    op.drop_table("operational_aggregates")
