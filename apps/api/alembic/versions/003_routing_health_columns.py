"""Add routing decision + provider health columns.

Adds the routing decision metadata to request logs, health-monitoring state to
providers, registry sync metadata to models, and an updated_at timestamp to
routing policies.

Revision ID: 003
Revises: 002
Create Date: 2024-01-03 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Provider health-monitoring state.
    op.add_column(
        "providers",
        sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "providers",
        sa.Column("last_health_latency_ms", sa.Float(), nullable=True),
    )
    op.add_column(
        "providers",
        sa.Column(
            "total_health_checks",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "providers",
        sa.Column(
            "failed_health_checks",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )

    # Model registry sync metadata.
    op.add_column(
        "models",
        sa.Column("average_latency_ms", sa.Float(), nullable=True),
    )
    op.add_column(
        "models",
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "models",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Routing decision metadata on request logs (no prompt content).
    op.add_column(
        "request_logs",
        sa.Column("requested_model", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "request_logs",
        sa.Column("routing_policy", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "request_logs",
        sa.Column("candidates_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "request_logs",
        sa.Column("fallback_count", sa.Integer(), nullable=True),
    )

    # Routing policies gain an updated_at timestamp.
    op.add_column(
        "routing_policies",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("routing_policies", "updated_at")
    op.drop_column("request_logs", "fallback_count")
    op.drop_column("request_logs", "candidates_count")
    op.drop_column("request_logs", "routing_policy")
    op.drop_column("request_logs", "requested_model")
    op.drop_column("models", "updated_at")
    op.drop_column("models", "last_synced_at")
    op.drop_column("models", "average_latency_ms")
    op.drop_column("providers", "failed_health_checks")
    op.drop_column("providers", "total_health_checks")
    op.drop_column("providers", "last_health_latency_ms")
    op.drop_column("providers", "last_health_check_at")
