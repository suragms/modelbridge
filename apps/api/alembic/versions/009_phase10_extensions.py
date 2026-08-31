"""Phase 10 extension ecosystem tables.

Revision ID: 009_phase10_extensions
Revises: 008_phase9_agents
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "009_phase10_extensions"
down_revision = "008_phase9_agents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "extension_registries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("registry_type", sa.String(30), server_default="local", nullable=False),
        sa.Column("base_url", sa.String(512)),
        sa.Column("encrypted_auth", sa.Text()),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_extension_registries_organization_id", "extension_registries", ["organization_id"])

    op.create_table(
        "extension_publishers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("homepage", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_extension_publishers_slug", "extension_publishers", ["slug"])

    op.create_table(
        "extension_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("registry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("extension_registries.id")),
        sa.Column("publisher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("extension_publishers.id")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("plugin_type", sa.String(30), nullable=False),
        sa.Column("trust_level", sa.String(20), server_default="unverified"),
        sa.Column("category", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("registry_id", "name", name="uq_package_registry_name"),
    )
    op.create_index("ix_extension_packages_name", "extension_packages", ["name"])
    op.create_index("ix_extension_packages_plugin_type", "extension_packages", ["plugin_type"])
    op.create_index("ix_extension_packages_trust_level", "extension_packages", ["trust_level"])

    op.create_table(
        "extension_package_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("package_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("extension_packages.id"), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("compatibility_version", sa.String(40), server_default="1.0.0"),
        sa.Column("manifest", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("permissions", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("configuration_schema", postgresql.JSONB()),
        sa.Column("entry_point", sa.String(255)),
        sa.Column("template_definition", postgresql.JSONB()),
        sa.Column("changelog", sa.Text()),
        sa.Column("published_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("published_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.UniqueConstraint("package_id", "version", name="uq_package_version"),
    )
    op.create_index("ix_extension_package_versions_package_id", "extension_package_versions", ["package_id"])

    op.create_table(
        "extension_installations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column(
            "package_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extension_package_versions.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), server_default="installed"),
        sa.Column("previous_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("extension_package_versions.id")),
        sa.Column("installed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("enabled_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("last_error", sa.Text()),
        sa.Column("health_status", sa.String(20), server_default="unknown"),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("failure_count", sa.Integer(), server_default="0"),
        sa.Column("execution_count", sa.Integer(), server_default="0"),
        sa.Column("avg_latency_ms", sa.Float()),
        sa.Column("installed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("enabled_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "package_version_id", name="uq_org_package_version"),
    )
    op.create_index("ix_extension_installations_organization_id", "extension_installations", ["organization_id"])
    op.create_index("ix_extension_installations_status", "extension_installations", ["status"])

    op.create_table(
        "extension_configurations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "installation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("extension_installations.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column("config", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("encrypted_secrets", sa.Text()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("extension_configurations")
    op.drop_table("extension_installations")
    op.drop_table("extension_package_versions")
    op.drop_table("extension_packages")
    op.drop_table("extension_publishers")
    op.drop_table("extension_registries")
