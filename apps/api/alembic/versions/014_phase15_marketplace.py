"""Phase 15 marketplace tables.

Revision ID: 014_phase15_marketplace
Revises: 013_phase14_platform
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "014_phase15_marketplace"
down_revision = "013_phase14_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("extension_publishers", sa.Column("description", sa.Text()))
    op.add_column("extension_publishers", sa.Column("website", sa.String(512)))
    op.add_column("extension_publishers", sa.Column("status", sa.String(20), server_default="active"))
    op.add_column(
        "extension_publishers",
        sa.Column("verification_status", sa.String(20), server_default="unverified"),
    )

    op.create_table(
        "marketplace_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("package_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("extension_packages.id"), unique=True, nullable=False),
        sa.Column("publisher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("extension_publishers.id")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("content_type", sa.String(30), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("category", sa.String(50)),
        sa.Column("status", sa.String(20), server_default="draft"),
        sa.Column("visibility", sa.String(20), server_default="public"),
        sa.Column("visibility_scope", sa.String(40), server_default="public"),
        sa.Column("featured", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("extension_package_versions.id")),
        sa.Column("security_review_status", sa.String(30), server_default="not_reviewed"),
        sa.Column("install_count", sa.Integer(), server_default="0"),
        sa.Column("view_count", sa.Integer(), server_default="0"),
        sa.Column("documentation_url", sa.String(512)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("slug", "visibility_scope", name="uq_marketplace_slug_scope"),
    )
    op.create_index("ix_marketplace_items_status", "marketplace_items", ["status"])
    op.create_index("ix_marketplace_items_content_type", "marketplace_items", ["content_type"])
    op.create_index("ix_marketplace_items_category", "marketplace_items", ["category"])
    op.create_index("ix_marketplace_items_slug", "marketplace_items", ["slug"])

    op.create_table(
        "marketplace_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("marketplace_items.id"), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("extension_package_versions.id"), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("validation_errors", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("security_review_status", sa.String(30), server_default="not_reviewed"),
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("review_notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_marketplace_submissions_item_id", "marketplace_submissions", ["item_id"])

    op.create_table(
        "marketplace_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("marketplace_items.id"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200)),
        sa.Column("body", sa.Text()),
        sa.Column("is_moderated", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("item_id", "organization_id", "reviewer_id", name="uq_review_per_org"),
    )

    op.create_table(
        "marketplace_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("marketplace_items.id"), nullable=False),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("reason", sa.String(80), nullable=False),
        sa.Column("details", sa.Text()),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("resolution_notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_marketplace_reports_status", "marketplace_reports", ["status"])

    op.create_table(
        "marketplace_install_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("marketplace_items.id"), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("extension_package_versions.id"), nullable=False),
        sa.Column("installation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("extension_installations.id")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("environment_id", postgresql.UUID(as_uuid=True)),
        sa.Column("action", sa.String(20), server_default="install"),
        sa.Column("previous_version_id", postgresql.UUID(as_uuid=True)),
        sa.Column("installed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("status", sa.String(20), server_default="completed"),
        sa.Column("reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_marketplace_install_history_org", "marketplace_install_history", ["organization_id"])

    op.create_table(
        "marketplace_analytics_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("marketplace_items.id"), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True)),
        sa.Column("event_metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_marketplace_analytics_item", "marketplace_analytics_events", ["item_id"])
    op.create_index("ix_marketplace_analytics_type", "marketplace_analytics_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("marketplace_analytics_events")
    op.drop_table("marketplace_install_history")
    op.drop_table("marketplace_reports")
    op.drop_table("marketplace_reviews")
    op.drop_table("marketplace_submissions")
    op.drop_table("marketplace_items")
    op.drop_column("extension_publishers", "verification_status")
    op.drop_column("extension_publishers", "status")
    op.drop_column("extension_publishers", "website")
    op.drop_column("extension_publishers", "description")
