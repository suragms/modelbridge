"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("role", sa.String(20), server_default="owner"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Organizations
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Add FK for users.organization_id
    op.create_foreign_key("fk_users_org", "users", "organizations", ["organization_id"], ["id"])

    # API Keys
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key_hash", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
    )

    # Providers
    op.create_table(
        "providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("base_url", sa.String(512)),
        sa.Column("status", sa.String(20), server_default="unknown"),
        sa.Column("is_enabled", sa.Boolean, server_default="true"),
        sa.Column("config", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
    )

    # Provider Credentials
    op.create_table(
        "provider_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("encrypted_key", sa.Text, nullable=False),
        sa.Column("key_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("providers.id"), nullable=False),
    )

    # Models
    op.create_table(
        "models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider_model_id", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("context_window", sa.Integer, server_default="4096"),
        sa.Column("input_price_per_1k", sa.Float, server_default="0"),
        sa.Column("output_price_per_1k", sa.Float, server_default="0"),
        sa.Column("supports_streaming", sa.Boolean, server_default="true"),
        sa.Column("supports_tools", sa.Boolean, server_default="false"),
        sa.Column("supports_embeddings", sa.Boolean, server_default="false"),
        sa.Column("supports_vision", sa.Boolean, server_default="false"),
        sa.Column("supports_json_mode", sa.Boolean, server_default="false"),
        sa.Column("is_enabled", sa.Boolean, server_default="true"),
        sa.Column("quality_score", sa.Float, server_default="0.5"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("providers.id"), nullable=False),
    )

    # Model Capabilities
    op.create_table(
        "model_capabilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("value", sa.String(255), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("models.id"), nullable=False),
    )

    # Routing Policies
    op.create_table(
        "routing_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("strategy", sa.String(50), nullable=False, server_default="auto"),
        sa.Column("is_default", sa.Boolean, server_default="false"),
        sa.Column("config", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Routing Rules
    op.create_table(
        "routing_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("condition_type", sa.String(50), nullable=False),
        sa.Column("condition_value", sa.String(255), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("target_model", sa.String(255)),
        sa.Column("priority", sa.Integer, server_default="0"),
        sa.Column("is_enabled", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("routing_policies.id"), nullable=False),
    )

    # Request Logs
    op.create_table(
        "request_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", sa.String(36), unique=True, nullable=False, index=True),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(255), nullable=False),
        sa.Column("latency_ms", sa.Float, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error", sa.Text),
        sa.Column("routing_strategy", sa.String(50)),
        sa.Column("fallback_used", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("api_keys.id")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
    )

    # Usage Records
    op.create_table(
        "usage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", sa.String(36), nullable=False, index=True),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(255), nullable=False),
        sa.Column("input_tokens", sa.Integer, server_default="0"),
        sa.Column("output_tokens", sa.Integer, server_default="0"),
        sa.Column("total_tokens", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
    )

    # Cost Records
    op.create_table(
        "cost_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", sa.String(36), nullable=False, index=True),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(255), nullable=False),
        sa.Column("input_cost", sa.Float, server_default="0"),
        sa.Column("output_cost", sa.Float, server_default="0"),
        sa.Column("total_cost", sa.Float, server_default="0"),
        sa.Column("is_estimated", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
    )

    # Health Checks
    op.create_table(
        "health_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("latency_ms", sa.Float, server_default="0"),
        sa.Column("error", sa.String(512)),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("providers.id"), nullable=False),
    )

    # Insert default routing policy
    op.execute(
        """INSERT INTO routing_policies (id, name, strategy, is_default, config)
        VALUES ('00000000-0000-0000-0000-000000000001', 'Default', 'balanced', true,
        '{"quality_weight": 0.35, "speed_weight": 0.30, "cost_weight": 0.20, "reliability_weight": 0.15}')"""
    )


def downgrade() -> None:
    op.drop_table("health_checks")
    op.drop_table("cost_records")
    op.drop_table("usage_records")
    op.drop_table("request_logs")
    op.drop_table("routing_rules")
    op.drop_table("routing_policies")
    op.drop_table("model_capabilities")
    op.drop_table("models")
    op.drop_table("provider_credentials")
    op.drop_table("providers")
    op.drop_table("api_keys")
    op.drop_table("users")
    op.drop_table("organizations")
