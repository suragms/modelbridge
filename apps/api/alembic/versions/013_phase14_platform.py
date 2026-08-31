"""Phase 14 developer platform tables.

Revision ID: 013_phase14_platform
Revises: 012_phase13_intelligence
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "013_phase14_platform"
down_revision = "012_phase13_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("source", sa.String(60), server_default="system"),
        sa.Column("schema_version", sa.String(10), server_default="1.0"),
        sa.Column("payload_metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("idempotency_key", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_platform_events_event_type", "platform_events", ["event_type"])
    op.create_index("ix_platform_events_organization_id", "platform_events", ["organization_id"])
    op.create_index("ix_platform_events_created_at", "platform_events", ["created_at"])

    op.create_table(
        "event_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("event_types", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_event_subscriptions_organization_id", "event_subscriptions", ["organization_id"])
    op.create_index("ix_event_subscriptions_target_id", "event_subscriptions", ["target_id"])

    op.create_table(
        "webhook_endpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("event_types", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("secret_encrypted", sa.Text(), nullable=False),
        sa.Column("secret_prefix", sa.String(12), server_default="whsec_..."),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_webhook_endpoints_organization_id", "webhook_endpoints", ["organization_id"])
    op.create_index("ix_webhook_endpoints_status", "webhook_endpoints", ["status"])

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("webhook_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("webhook_endpoints.id"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_events.id"), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), server_default="0"),
        sa.Column("max_attempts", sa.Integer(), server_default="5"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("next_retry_at", sa.DateTime(timezone=True)),
        sa.Column("response_status", sa.Integer()),
        sa.Column("failure_category", sa.String(40)),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_webhook_deliveries_webhook_id", "webhook_deliveries", ["webhook_id"])
    op.create_index("ix_webhook_deliveries_status", "webhook_deliveries", ["status"])
    op.create_index("ix_webhook_deliveries_idempotency_key", "webhook_deliveries", ["idempotency_key"])

    op.create_table(
        "integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("config", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("credential_encrypted", sa.Text()),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "provider", "name", name="uq_org_integration"),
    )
    op.create_index("ix_integrations_organization_id", "integrations", ["organization_id"])
    op.create_index("ix_integrations_provider", "integrations", ["provider"])

    op.create_table(
        "automations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("trigger_type", sa.String(30), nullable=False),
        sa.Column("trigger_config", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("action_type", sa.String(30), nullable=False),
        sa.Column("action_config", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("template_id", sa.String(80)),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("requires_approval", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_automations_organization_id", "automations", ["organization_id"])
    op.create_index("ix_automations_status", "automations", ["status"])

    op.create_table(
        "automation_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("automation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("automations.id"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_events.id")),
        sa.Column("workflow_execution_id", postgresql.UUID(as_uuid=True)),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("trigger_summary", sa.Text()),
        sa.Column("result_summary", postgresql.JSONB()),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_automation_executions_organization_id", "automation_executions", ["organization_id"])
    op.create_index("ix_automation_executions_automation_id", "automation_executions", ["automation_id"])

    op.add_column("api_keys", sa.Column("last_used_ip", sa.String(45)))
    op.add_column("api_keys", sa.Column("rotated_from_id", postgresql.UUID(as_uuid=True)))


def downgrade() -> None:
    op.drop_column("api_keys", "rotated_from_id")
    op.drop_column("api_keys", "last_used_ip")
    op.drop_table("automation_executions")
    op.drop_table("automations")
    op.drop_table("integrations")
    op.drop_table("webhook_deliveries")
    op.drop_table("webhook_endpoints")
    op.drop_table("event_subscriptions")
    op.drop_table("platform_events")
