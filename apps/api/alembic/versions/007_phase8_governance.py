"""Phase 8 AI governance tables.

Revision ID: 007_phase8_governance
Revises: 006_phase5_production
Create Date: 2026-08-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "007_phase8_governance"
down_revision = "006_phase5_production"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("providers", sa.Column("region", sa.String(64), nullable=True))
    op.add_column("providers", sa.Column("data_residency", sa.String(64), nullable=True))
    op.add_column("providers", sa.Column("deployment_type", sa.String(20), nullable=True))

    op.create_table(
        "governance_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("policy_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("rules", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("action", sa.String(40), nullable=False, server_default="deny"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_governance_policies_organization_id", "governance_policies", ["organization_id"])

    op.create_table(
        "governance_policy_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("governance_policies.id"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("rules", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_gov_policy_versions_policy_id", "governance_policy_versions", ["policy_id"])
    op.create_index("ix_gov_policy_versions_org_id", "governance_policy_versions", ["organization_id"])

    op.create_table(
        "governance_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("decision", sa.String(40), nullable=True),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("governance_policies.id"), nullable=True),
        sa.Column("policy_name", sa.String(255), nullable=True),
        sa.Column("policy_type", sa.String(50), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=True),
        sa.Column("classification", sa.String(40), nullable=True),
        sa.Column("detection_categories", postgresql.JSONB(), nullable=True),
        sa.Column("requested_model", sa.String(255), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_governance_events_org_id", "governance_events", ["organization_id"])
    op.create_index("ix_governance_events_type", "governance_events", ["event_type"])
    op.create_index("ix_governance_events_created", "governance_events", ["created_at"])
    op.create_index("ix_governance_events_risk", "governance_events", ["risk_level"])
    op.create_index("ix_governance_events_request_id", "governance_events", ["request_id"])

    op.create_table(
        "governance_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("request_type", sa.String(40), nullable=False, server_default="chat"),
        sa.Column("risk_level", sa.String(20), nullable=True),
        sa.Column("classification", sa.String(40), nullable=True),
        sa.Column("matched_policy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("governance_policies.id"), nullable=True),
        sa.Column("matched_policy_name", sa.String(255), nullable=True),
        sa.Column("requested_model", sa.String(255), nullable=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("safe_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_governance_approvals_org_id", "governance_approvals", ["organization_id"])
    op.create_index("ix_governance_approvals_status", "governance_approvals", ["status"])
    op.create_index("ix_governance_approvals_fingerprint", "governance_approvals", ["fingerprint"])

    op.create_table(
        "governance_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("governance_events.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_governance_notifications_org_id", "governance_notifications", ["organization_id"])

    op.create_table(
        "governance_settings",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), primary_key=True),
        sa.Column("pii_detection_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("secret_detection_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("redact_prompts", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("redact_responses", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("block_on_secret", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("block_sensitive_to_cloud", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("require_local_for_high_risk", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("allow_cloud_providers", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("allow_local_providers", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("content_safety_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("approval_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("approval_ttl_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("governance_settings")
    op.drop_table("governance_notifications")
    op.drop_table("governance_approvals")
    op.drop_table("governance_events")
    op.drop_table("governance_policy_versions")
    op.drop_table("governance_policies")
    op.drop_column("providers", "deployment_type")
    op.drop_column("providers", "data_residency")
    op.drop_column("providers", "region")
