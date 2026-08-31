"""Managed instance lifecycle for cloud deployments."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud import InstanceLifecycleStatus
from app.models.enterprise import InstanceStatus, ManagedInstance
from app.services.enterprise.activity import record_activity
from app.services.enterprise.fleet import FleetService
from app.services.metrics import record_managed_instance_lifecycle

LIFECYCLE_TRANSITIONS = {
    InstanceLifecycleStatus.PROVISIONING: {InstanceLifecycleStatus.ACTIVE, InstanceLifecycleStatus.FAILED},
    InstanceLifecycleStatus.ACTIVE: {
        InstanceLifecycleStatus.UPDATING,
        InstanceLifecycleStatus.DEGRADED,
        InstanceLifecycleStatus.FAILED,
        InstanceLifecycleStatus.DECOMMISSIONED,
    },
    InstanceLifecycleStatus.UPDATING: {
        InstanceLifecycleStatus.ACTIVE,
        InstanceLifecycleStatus.DEGRADED,
        InstanceLifecycleStatus.FAILED,
    },
    InstanceLifecycleStatus.DEGRADED: {
        InstanceLifecycleStatus.ACTIVE,
        InstanceLifecycleStatus.FAILED,
        InstanceLifecycleStatus.DECOMMISSIONED,
    },
    InstanceLifecycleStatus.FAILED: {
        InstanceLifecycleStatus.PROVISIONING,
        InstanceLifecycleStatus.DECOMMISSIONED,
    },
    InstanceLifecycleStatus.DECOMMISSIONED: set(),
}


class CloudInstanceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.fleet = FleetService(db)

    async def list_instances(
        self,
        organization_id: uuid.UUID,
        *,
        region_id: uuid.UUID | None = None,
    ) -> list[ManagedInstance]:
        q = select(ManagedInstance).where(ManagedInstance.organization_id == organization_id)
        if region_id:
            q = q.where(ManagedInstance.region_id == region_id)
        result = await self.db.execute(q.order_by(ManagedInstance.created_at.desc()))
        return list(result.scalars().all())

    async def get_instance(self, organization_id: uuid.UUID, instance_id: uuid.UUID) -> ManagedInstance | None:
        inst = await self.db.get(ManagedInstance, instance_id)
        if not inst or inst.organization_id != organization_id:
            return None
        return inst

    async def provision(
        self,
        *,
        org_id: uuid.UUID,
        name: str,
        endpoint: str,
        region_id: uuid.UUID | None,
        plane_type: str,
        environment_kind: str | None,
        registered_by: uuid.UUID | None,
    ) -> tuple[ManagedInstance, str]:
        instance, token = await self.fleet.register(
            org_id=org_id,
            name=name,
            endpoint=endpoint,
            environment_kind=environment_kind,
            registered_by=registered_by,
        )
        instance.region_id = region_id
        instance.lifecycle_status = InstanceLifecycleStatus.PROVISIONING
        instance.plane_type = plane_type
        record_managed_instance_lifecycle("provisioned")
        await self.db.flush()
        return instance, token

    async def activate(self, instance: ManagedInstance) -> ManagedInstance:
        return await self._transition(instance, InstanceLifecycleStatus.ACTIVE, health=InstanceStatus.HEALTHY)

    async def transition(
        self,
        instance: ManagedInstance,
        target: str,
        *,
        actor_id: uuid.UUID | None = None,
        reason: str | None = None,
    ) -> ManagedInstance:
        current = instance.lifecycle_status or InstanceLifecycleStatus.PROVISIONING
        allowed = LIFECYCLE_TRANSITIONS.get(current, set())
        if target not in allowed and current != target:
            raise ValueError(f"Invalid lifecycle transition: {current} -> {target}")

        instance.lifecycle_status = target
        if target == InstanceLifecycleStatus.ACTIVE:
            instance.status = InstanceStatus.HEALTHY
        elif target == InstanceLifecycleStatus.DEGRADED:
            instance.status = InstanceStatus.DEGRADED
        elif target == InstanceLifecycleStatus.FAILED:
            instance.status = InstanceStatus.UNHEALTHY
        elif target == InstanceLifecycleStatus.DECOMMISSIONED:
            instance.status = InstanceStatus.OFFLINE

        record_managed_instance_lifecycle(target)
        await record_activity(
            self.db,
            organization_id=instance.organization_id,
            event_type="instance.lifecycle",
            resource_type="instance",
            resource_id=str(instance.id),
            actor_id=actor_id,
            metadata={"from": current, "to": target, "reason": reason},
        )
        await self.db.flush()
        return instance

    async def _transition(
        self,
        instance: ManagedInstance,
        target: str,
        *,
        health: str | None = None,
    ) -> ManagedInstance:
        instance.lifecycle_status = target
        if health:
            instance.status = health
        record_managed_instance_lifecycle(target)
        await self.db.flush()
        return instance

    async def on_heartbeat(self, instance: ManagedInstance, status: str) -> None:
        if instance.lifecycle_status == InstanceLifecycleStatus.PROVISIONING and status in {
            InstanceStatus.HEALTHY,
            InstanceStatus.DEGRADED,
        }:
            instance.lifecycle_status = InstanceLifecycleStatus.ACTIVE
            record_managed_instance_lifecycle("active")
        elif status == InstanceStatus.DEGRADED and instance.lifecycle_status == InstanceLifecycleStatus.ACTIVE:
            instance.lifecycle_status = InstanceLifecycleStatus.DEGRADED
        elif status in {InstanceStatus.UNHEALTHY, InstanceStatus.OFFLINE}:
            if instance.lifecycle_status in {
                InstanceLifecycleStatus.ACTIVE,
                InstanceLifecycleStatus.UPDATING,
            }:
                instance.lifecycle_status = InstanceLifecycleStatus.DEGRADED
