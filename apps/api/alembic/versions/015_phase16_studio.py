"""Phase 16 AI Studio tables.

Revision ID: 015_phase16_studio
Revises: 014_phase15_marketplace
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "015_phase16_studio"
down_revision = "014_phase15_marketplace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("tags", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("usage_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_prompt_templates_org", "prompt_templates", ["organization_id"])

    op.create_table(
        "prompt_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("prompt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prompt_templates.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("variables", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("change_notes", sa.Text()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("prompt_id", "version", name="uq_prompt_version"),
    )

    op.create_table(
        "evaluation_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("test_cases", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "evaluation_suites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evaluation_datasets.id"), nullable=False),
        sa.Column("prompt_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prompt_versions.id")),
        sa.Column("model", sa.String(255), server_default="auto"),
        sa.Column("parameters", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("scorers", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "evaluation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("suite_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evaluation_suites.id"), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("pass_count", sa.Integer(), server_default="0"),
        sa.Column("fail_count", sa.Integer(), server_default="0"),
        sa.Column("total_latency_ms", sa.Float(), server_default="0"),
        sa.Column("total_tokens", sa.Integer(), server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float()),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_evaluation_runs_status", "evaluation_runs", ["status"])

    op.create_table(
        "evaluation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evaluation_runs.id"), nullable=False),
        sa.Column("case_index", sa.Integer(), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("expected", sa.Text()),
        sa.Column("actual_output", sa.Text()),
        sa.Column("passed", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("scorer", sa.String(40), server_default="exact_match"),
        sa.Column("score_detail", sa.Text()),
        sa.Column("latency_ms", sa.Float()),
        sa.Column("tokens_used", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "studio_workflow_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflows.id"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("visual_definition", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("change_summary", sa.Text()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("workflow_id", "version", name="uq_studio_wf_version"),
    )

    op.create_table(
        "studio_agent_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("config_snapshot", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("change_summary", sa.Text()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("agent_id", "version", name="uq_studio_agent_version"),
    )

    op.create_table(
        "studio_deployments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("resource_type", sa.String(30), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("environment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("environments.id")),
        sa.Column("status", sa.String(30), server_default="draft"),
        sa.Column("pipeline_state", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("deployed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_studio_deployments_status", "studio_deployments", ["status"])

    op.create_table(
        "studio_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("resource_type", sa.String(30), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "studio_collaborators",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("resource_type", sa.String(30), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(20), server_default="editor"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("resource_type", "resource_id", "user_id", name="uq_studio_collab"),
    )

    op.create_table(
        "studio_version_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("resource_type", sa.String(30), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("change_summary", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("studio_version_history")
    op.drop_table("studio_collaborators")
    op.drop_table("studio_comments")
    op.drop_table("studio_deployments")
    op.drop_table("studio_agent_versions")
    op.drop_table("studio_workflow_versions")
    op.drop_table("evaluation_results")
    op.drop_table("evaluation_runs")
    op.drop_table("evaluation_suites")
    op.drop_table("evaluation_datasets")
    op.drop_table("prompt_versions")
    op.drop_table("prompt_templates")
