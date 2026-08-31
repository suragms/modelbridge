"""Phase 12 cloud architecture: regions, metering, quotas, incidents, rollouts.

Revision ID: 011_phase12_cloud
Revises: 010_phase11_enterprise
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "011_phase12_cloud"
down_revision = "010_phase11_enterprise"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "regions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("location", sa.String(255)),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("capabilities", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("data_residency_zones", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("code", name="uq_region_code"),
    )
    op.create_index("ix_regions_code", "regions", ["code"])
    op.create_index("ix_regions_status", "regions", ["status"])

    op.add_column("managed_instances", sa.Column("region_id", postgresql.UUID(as_uuid=True)))
    op.add_column("managed_instances", sa.Column("lifecycle_status", sa.String(20), server_default="provisioning"))
    op.add_column("managed_instances", sa.Column("plane_type", sa.String(20), server_default="data"))
    op.create_foreign_key(
        "fk_managed_instances_region_id",
        "managed_instances",
        "regions",
        ["region_id"],
        ["id"],
    )
    op.create_index("ix_managed_instances_region_id", "managed_instances", ["region_id"])
    op.create_index("ix_managed_instances_lifecycle_status", "managed_instances", ["lifecycle_status"])

    op.create_table(
        "cloud_incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("region_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("regions.id")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("severity", sa.String(20), server_default="medium"),
        sa.Column("status", sa.String(20), server_default="open"),
        sa.Column("affected_service", sa.String(100)),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_cloud_incidents_organization_id", "cloud_incidents", ["organization_id"])
    op.create_index("ix_cloud_incidents_status", "cloud_incidents", ["status"])

    op.create_table(
        "usage_meter_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id")),
        sa.Column("environment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("environments.id")),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("quantity", sa.Float(), server_default="1", nullable=False),
        sa.Column("metadata", postgresql.JSONB()),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_usage_meter_events_organization_id", "usage_meter_events", ["organization_id"])
    op.create_index("ix_usage_meter_events_event_type", "usage_meter_events", ["event_type"])
    op.create_index("ix_usage_meter_events_recorded_at", "usage_meter_events", ["recorded_at"])

    op.create_table(
        "quotas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("resource", sa.String(40), nullable=False),
        sa.Column("period", sa.String(20), server_default="daily"),
        sa.Column("limit_value", sa.Float(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "resource", "period", name="uq_org_quota_resource_period"),
    )
    op.create_index("ix_quotas_organization_id", "quotas", ["organization_id"])

    op.create_table(
        "scoped_configurations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("scope_ref_id", postgresql.UUID(as_uuid=True)),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("config", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("change_summary", sa.Text()),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("scope", "scope_ref_id", "version", name="uq_scoped_config_version"),
    )
    op.create_index("ix_scoped_configurations_scope", "scoped_configurations", ["scope"])
    op.create_index("ix_scoped_configurations_organization_id", "scoped_configurations", ["organization_id"])

    op.create_table(
        "configuration_rollouts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("scoped_configuration_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scoped_configurations.id")),
        sa.Column("configuration_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("configuration_versions.id")),
        sa.Column("region_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("regions.id")),
        sa.Column("configuration_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("deployed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_configuration_rollouts_region_id", "configuration_rollouts", ["region_id"])
    op.create_index("ix_configuration_rollouts_status", "configuration_rollouts", ["status"])

    op.create_table(
        "service_registrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("service_name", sa.String(100), nullable=False),
        sa.Column("region_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("regions.id"), nullable=False),
        sa.Column("endpoint", sa.String(512), nullable=False),
        sa.Column("plane_type", sa.String(20), server_default="data"),
        sa.Column("health_status", sa.String(20), server_default="unknown"),
        sa.Column("capabilities", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("service_name", "region_id", name="uq_service_region"),
    )
    op.create_index("ix_service_registrations_service_name", "service_registrations", ["service_name"])

    op.create_table(
        "failover_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id")),
        sa.Column("region_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("regions.id")),
        sa.Column("source_service", sa.String(100), nullable=False),
        sa.Column("target_service", sa.String(100), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("verified", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("metadata", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_failover_events_organization_id", "failover_events", ["organization_id"])

    op.create_table(
        "cloud_onboarding",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("selected_region_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("regions.id")),
        sa.Column("data_residency_policy", sa.String(20), server_default="global"),
        sa.Column("steps_completed", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("is_complete", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", name="uq_cloud_onboarding_org"),
    )
    op.create_index("ix_cloud_onboarding_organization_id", "cloud_onboarding", ["organization_id"])


def downgrade() -> None:
    op.drop_table("cloud_onboarding")
    op.drop_table("failover_events")
    op.drop_table("service_registrations")
    op.drop_table("configuration_rollouts")
    op.drop_table("scoped_configurations")
    op.drop_table("quotas")
    op.drop_table("usage_meter_events")
    op.drop_table("cloud_incidents")
    op.drop_constraint("fk_managed_instances_region_id", "managed_instances", type_="foreignkey")
    op.drop_index("ix_managed_instances_lifecycle_status", "managed_instances")
    op.drop_index("ix_managed_instances_region_id", "managed_instances")
    op.drop_column("managed_instances", "plane_type")
    op.drop_column("managed_instances", "lifecycle_status")
    op.drop_column("managed_instances", "region_id")
    op.drop_table("regions")
