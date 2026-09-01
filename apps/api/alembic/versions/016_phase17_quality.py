"""Phase 17 AI Quality & Reliability Platform tables.

Revision ID: 016_phase17_quality
Revises: 015_phase16_studio
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "016_phase17_quality"
down_revision = "015_phase16_studio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quality_pipelines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("input_source", sa.String(50), server_default="dataset"),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evaluation_datasets.id")),
        sa.Column("schedule", sa.String(100)),
        sa.Column("trigger_on", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_quality_pipelines_org", "quality_pipelines", ["organization_id"])

    op.create_table(
        "quality_pipeline_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quality_pipelines.id"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("evaluators", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("thresholds", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("prompt_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prompt_versions.id")),
        sa.Column("model", sa.String(255), server_default="auto"),
        sa.Column("parameters", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("change_summary", sa.Text()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("pipeline_id", "version", name="uq_quality_pipeline_version"),
    )

    op.create_table(
        "quality_evaluation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quality_pipelines.id"), nullable=False),
        sa.Column("pipeline_version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("pipeline_version", sa.Integer()),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("trigger", sa.String(50), server_default="manual"),
        sa.Column("pass_count", sa.Integer(), server_default="0"),
        sa.Column("fail_count", sa.Integer(), server_default="0"),
        sa.Column("pass_rate", sa.Float()),
        sa.Column("total_latency_ms", sa.Float(), server_default="0"),
        sa.Column("total_tokens", sa.Integer(), server_default="0"),
        sa.Column("total_cost", sa.Float()),
        sa.Column("evaluator_results", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("evidence", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("started_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_quality_eval_runs_org", "quality_evaluation_runs", ["organization_id"])

    op.create_table(
        "quality_regression_comparisons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("comparison_type", sa.String(50), nullable=False),
        sa.Column("baseline_label", sa.String(255), nullable=False),
        sa.Column("candidate_label", sa.String(255), nullable=False),
        sa.Column("baseline_run_id", postgresql.UUID(as_uuid=True)),
        sa.Column("candidate_run_id", postgresql.UUID(as_uuid=True)),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True)),
        sa.Column("metrics", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("differences", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("status", sa.String(30), server_default="insufficient_data"),
        sa.Column("thresholds", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "quality_production_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), unique=True, nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="false"),
        sa.Column("sampling_rate", sa.Float(), server_default="0.01"),
        sa.Column("sampling_rules", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("redaction_policy", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("retention_days", sa.Integer(), server_default="30"),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quality_pipelines.id")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "quality_production_samples",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("model", sa.String(255)),
        sa.Column("provider", sa.String(255)),
        sa.Column("latency_ms", sa.Float()),
        sa.Column("status", sa.String(20)),
        sa.Column("redacted_metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("quality_signals", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_quality_prod_samples_org", "quality_production_samples", ["organization_id"])

    op.create_table(
        "quality_gates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("pipeline_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quality_pipelines.id"), nullable=False),
        sa.Column("min_pass_rate", sa.Float(), server_default="0.9"),
        sa.Column("min_safety_score", sa.Float()),
        sa.Column("max_regression_delta", sa.Float()),
        sa.Column("block_deployment", sa.Boolean(), server_default="true"),
        sa.Column("enabled", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "quality_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True)),
        sa.Column("gate_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "quality_incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quality_alerts.id")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("affected_version", sa.String(255)),
        sa.Column("evidence", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("resolution", sa.Text()),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "quality_scorecards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("scorecard_type", sa.String(30), nullable=False),
        sa.Column("time_range", sa.String(30), server_default="7d"),
        sa.Column("overall_score", sa.Float()),
        sa.Column("dimensions", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("formula", sa.Text(), nullable=False),
        sa.Column("inputs", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("limitations", sa.Text(), nullable=False),
        sa.Column("confidence", sa.String(20)),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "quality_trend_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("metric", sa.String(50), nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("sample_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_quality_trends_org_metric", "quality_trend_points", ["organization_id", "metric"])


def downgrade() -> None:
    for table in (
        "quality_trend_points",
        "quality_scorecards",
        "quality_incidents",
        "quality_alerts",
        "quality_gates",
        "quality_production_samples",
        "quality_production_configs",
        "quality_regression_comparisons",
        "quality_evaluation_runs",
        "quality_pipeline_versions",
        "quality_pipelines",
    ):
        op.drop_table(table)
