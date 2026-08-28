"""Phase 3 observability schema

Revision ID: 004
Revises: 003
Create Date: 2026-08-28 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- request_logs lifecycle fields ---
    op.alter_column("request_logs", "request_id", type_=sa.String(64), existing_type=sa.String(36))
    op.add_column("request_logs", sa.Column("selected_model", sa.String(255), nullable=True))
    op.add_column("request_logs", sa.Column("provider_latency_ms", sa.Float(), nullable=True))
    op.add_column("request_logs", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("request_logs", sa.Column("error_code", sa.String(50), nullable=True))
    op.add_column("request_logs", sa.Column("error_type", sa.String(50), nullable=True))

    # Migrate legacy status values
    op.execute("UPDATE request_logs SET status = 'COMPLETED' WHERE status = 'success'")
    op.execute("UPDATE request_logs SET status = 'FAILED' WHERE status = 'error'")
    op.execute("UPDATE request_logs SET selected_model = model WHERE selected_model IS NULL")

    # --- usage_records ---
    op.add_column(
        "usage_records",
        sa.Column("usage_source", sa.String(30), server_default="UNAVAILABLE", nullable=False),
    )

    # --- cost_records ---
    op.add_column(
        "cost_records",
        sa.Column("pricing_source", sa.String(30), server_default="UNKNOWN", nullable=False),
    )
    op.add_column(
        "cost_records",
        sa.Column("currency", sa.String(10), server_default="USD", nullable=False),
    )

    # --- model pricing registry fields ---
    op.add_column(
        "models",
        sa.Column("input_price_per_million", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column(
        "models",
        sa.Column("output_price_per_million", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column(
        "models",
        sa.Column("pricing_source", sa.String(30), server_default="UNKNOWN", nullable=False),
    )
    op.add_column(
        "models",
        sa.Column("pricing_currency", sa.String(10), server_default="USD", nullable=False),
    )
    op.add_column("models", sa.Column("pricing_updated_at", sa.DateTime(timezone=True), nullable=True))

    # Backfill per-million from per-1k pricing
    op.execute(
        "UPDATE models SET input_price_per_million = input_price_per_1k * 1000, "
        "output_price_per_million = output_price_per_1k * 1000 "
        "WHERE input_price_per_million = 0 AND output_price_per_million = 0 "
        "AND (input_price_per_1k > 0 OR output_price_per_1k > 0)"
    )

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    # --- performance indexes ---
    op.create_index("ix_request_logs_created_at", "request_logs", ["created_at"])
    op.create_index("ix_request_logs_status", "request_logs", ["status"])
    op.create_index("ix_request_logs_provider", "request_logs", ["provider"])
    op.create_index("ix_request_logs_model", "request_logs", ["model"])
    op.create_index("ix_request_logs_org_id", "request_logs", ["organization_id"])
    op.create_index("ix_usage_records_created_at", "usage_records", ["created_at"])
    op.create_index("ix_cost_records_created_at", "cost_records", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_cost_records_created_at", "cost_records")
    op.drop_index("ix_usage_records_created_at", "usage_records")
    op.drop_index("ix_request_logs_org_id", "request_logs")
    op.drop_index("ix_request_logs_model", "request_logs")
    op.drop_index("ix_request_logs_provider", "request_logs")
    op.drop_index("ix_request_logs_status", "request_logs")
    op.drop_index("ix_request_logs_created_at", "request_logs")
    op.drop_index("ix_audit_logs_action", "audit_logs")
    op.drop_index("ix_audit_logs_created_at", "audit_logs")
    op.drop_table("audit_logs")

    op.drop_column("models", "pricing_updated_at")
    op.drop_column("models", "pricing_currency")
    op.drop_column("models", "pricing_source")
    op.drop_column("models", "output_price_per_million")
    op.drop_column("models", "input_price_per_million")

    op.drop_column("cost_records", "currency")
    op.drop_column("cost_records", "pricing_source")
    op.drop_column("usage_records", "usage_source")

    op.drop_column("request_logs", "error_type")
    op.drop_column("request_logs", "error_code")
    op.drop_column("request_logs", "completed_at")
    op.drop_column("request_logs", "provider_latency_ms")
    op.drop_column("request_logs", "selected_model")

    op.execute("UPDATE request_logs SET status = 'success' WHERE status = 'COMPLETED'")
    op.execute("UPDATE request_logs SET status = 'error' WHERE status = 'FAILED'")
    op.alter_column("request_logs", "request_id", type_=sa.String(36), existing_type=sa.String(64))
