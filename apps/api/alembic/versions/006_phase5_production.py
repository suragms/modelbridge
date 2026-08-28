"""Phase 5 production: organizations, RBAC, scopes, limits, jobs.

Revision ID: 006_phase5_production
Revises: 005_phase4_capabilities
Create Date: 2026-08-28
"""

from __future__ import annotations

import re
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "006_phase5_production"
down_revision = "005_phase4_capabilities"
branch_labels = None
depends_on = None


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:60] or "org"


def upgrade() -> None:
    # --- organizations: slug, description, updated_at ---
    op.add_column("organizations", sa.Column("slug", sa.String(80), nullable=True))
    op.add_column("organizations", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "organizations",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )

    conn = op.get_bind()
    orgs = conn.execute(sa.text("SELECT id, name FROM organizations")).fetchall()
    seen: set[str] = set()
    for org_id, name in orgs:
        base = _slugify(name or "org")
        slug = base
        n = 1
        while slug in seen:
            slug = f"{base}-{n}"
            n += 1
        seen.add(slug)
        conn.execute(
            sa.text("UPDATE organizations SET slug = :slug WHERE id = :id"),
            {"slug": slug, "id": org_id},
        )

    op.alter_column("organizations", "slug", nullable=False)
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    # --- organization memberships ---
    op.create_table(
        "organization_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
    )
    op.create_index("ix_organization_members_user_id", "organization_members", ["user_id"])

    # Backfill memberships from users.organization_id
    users = conn.execute(
        sa.text("SELECT id, organization_id, role FROM users WHERE organization_id IS NOT NULL")
    ).fetchall()
    for user_id, org_id, role in users:
        conn.execute(
            sa.text(
                "INSERT INTO organization_members (id, organization_id, user_id, role, created_at) "
                "VALUES (:id, :org_id, :user_id, :role, now())"
            ),
            {"id": str(uuid.uuid4()), "org_id": org_id, "user_id": user_id, "role": role or "owner"},
        )

    # --- organization settings ---
    op.create_table(
        "organization_settings",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), primary_key=True),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("rate_limit_per_day", sa.Integer(), nullable=False, server_default="10000"),
        sa.Column("monthly_token_limit", sa.BigInteger(), nullable=True),
        sa.Column("monthly_budget_usd", sa.Float(), nullable=True),
        sa.Column("budget_warning_percent", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("budget_hard_limit_percent", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("request_log_retention_days", sa.Integer(), nullable=True),
        sa.Column("analytics_retention_days", sa.Integer(), nullable=True),
        sa.Column("audit_log_retention_days", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    for org_id, _ in orgs:
        conn.execute(
            sa.text("INSERT INTO organization_settings (organization_id) VALUES (:id)"),
            {"id": org_id},
        )

    # --- budget alerts ---
    op.create_table(
        "budget_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("api_keys.id"), nullable=True),
        sa.Column("alert_type", sa.String(40), nullable=False),
        sa.Column("threshold_percent", sa.Integer(), nullable=False),
        sa.Column("estimated_spend_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("budget_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_budget_alerts_org_id", "budget_alerts", ["organization_id"])

    # --- job runs ---
    op.create_table(
        "job_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("job_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("records_processed", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_job_runs_job_name", "job_runs", ["job_name"])
    op.create_index("ix_job_runs_started_at", "job_runs", ["started_at"])

    # --- organization invites (token-based, no email delivery) ---
    op.create_table(
        "organization_invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("email_hint", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # --- api_keys: scopes, limits, created_by ---
    op.add_column(
        "api_keys",
        sa.Column("scopes", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    op.add_column("api_keys", sa.Column("monthly_token_limit", sa.BigInteger(), nullable=True))
    op.add_column("api_keys", sa.Column("monthly_budget_usd", sa.Float(), nullable=True))
    op.add_column("api_keys", sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True))
    conn.execute(sa.text("UPDATE api_keys SET created_by_id = user_id WHERE created_by_id IS NULL"))
    op.create_foreign_key("fk_api_keys_created_by", "api_keys", "users", ["created_by_id"], ["id"])

    # --- routing policies: org scope ---
    op.add_column(
        "routing_policies",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_routing_policies_org", "routing_policies", "organizations", ["organization_id"], ["id"]
    )
    op.drop_constraint("routing_policies_name_key", "routing_policies", type_="unique")
    op.create_index("ix_routing_policies_org_name", "routing_policies", ["organization_id", "name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_routing_policies_org_name", "routing_policies")
    op.create_unique_constraint("routing_policies_name_key", "routing_policies", ["name"])
    op.drop_constraint("fk_routing_policies_org", "routing_policies", type_="foreignkey")
    op.drop_column("routing_policies", "organization_id")

    op.drop_constraint("fk_api_keys_created_by", "api_keys", type_="foreignkey")
    op.drop_column("api_keys", "created_by_id")
    op.drop_column("api_keys", "monthly_budget_usd")
    op.drop_column("api_keys", "monthly_token_limit")
    op.drop_column("api_keys", "scopes")

    op.drop_table("organization_invites")
    op.drop_index("ix_job_runs_started_at", "job_runs")
    op.drop_index("ix_job_runs_job_name", "job_runs")
    op.drop_table("job_runs")
    op.drop_index("ix_budget_alerts_org_id", "budget_alerts")
    op.drop_table("budget_alerts")
    op.drop_table("organization_settings")
    op.drop_index("ix_organization_members_user_id", "organization_members")
    op.drop_table("organization_members")

    op.drop_index("ix_organizations_slug", "organizations")
    op.drop_column("organizations", "updated_at")
    op.drop_column("organizations", "description")
    op.drop_column("organizations", "slug")
