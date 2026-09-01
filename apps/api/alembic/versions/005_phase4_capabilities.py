"""Phase 4 advanced capabilities and request metadata

Revision ID: 005
Revises: 004
Create Date: 2026-08-28 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "005_phase4_capabilities"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "models",
        sa.Column("supports_chat", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column(
        "models",
        sa.Column(
            "supports_structured_output", sa.Boolean(), server_default="false", nullable=False
        ),
    )
    op.add_column(
        "models",
        sa.Column("supports_tool_choice", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "models",
        sa.Column("supports_reasoning", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column("models", sa.Column("embedding_dimensions", sa.Integer(), nullable=True))
    op.add_column("models", sa.Column("max_output_tokens", sa.Integer(), nullable=True))

    # Embedding-only models should not be treated as chat models.
    op.execute(
        "UPDATE models SET supports_chat = false "
        "WHERE supports_embeddings = true AND supports_chat = true "
        "AND supports_tools = false AND supports_vision = false "
        "AND (LOWER(provider_model_id) LIKE '%embed%' "
        "OR LOWER(display_name) LIKE '%embed%')"
    )
    op.execute(
        "UPDATE models SET supports_tool_choice = true WHERE supports_tools = true"
    )

    op.add_column(
        "request_logs",
        sa.Column("request_type", sa.String(30), server_default="chat", nullable=False),
    )
    op.add_column(
        "request_logs",
        sa.Column("required_capabilities", sa.String(255), nullable=True),
    )
    op.add_column("request_logs", sa.Column("input_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("request_logs", "input_count")
    op.drop_column("request_logs", "required_capabilities")
    op.drop_column("request_logs", "request_type")
    op.drop_column("models", "max_output_tokens")
    op.drop_column("models", "embedding_dimensions")
    op.drop_column("models", "supports_reasoning")
    op.drop_column("models", "supports_tool_choice")
    op.drop_column("models", "supports_structured_output")
    op.drop_column("models", "supports_chat")
