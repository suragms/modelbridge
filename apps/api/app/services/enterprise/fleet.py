"""Fleet instance registration, authentication, and heartbeats."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enterprise import InstanceHeartbeat, InstanceStatus, ManagedInstance, SyncStatus
from app.models.governance import GovernancePolicy, PolicyStatus
from app.models.enterprise import PolicySyncRecord
from app.services.metrics import record_instance_heartbeat

HEARTBEAT_STALE_SECONDS = 300


def generate_instance_credential() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash


def verify_instance_credential(token: str, credential_hash: str) -> bool:
    return hashlib.sha256(token.encode()).hexdigest() == credential_hash


class FleetService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(
        self,
        *,
        org_id: uuid.UUID,
        name: str,
        endpoint: str,
        environment_kind: str | None,
        registered_by: uuid.UUID | None,
    ) -> tuple[ManagedInstance, str]:
        token, token_hash = generate_instance_credential()
        instance = ManagedInstance(
            organization_id=org_id,
            name=name,
            endpoint=endpoint.rstrip("/"),
            environment_kind=environment_kind,
            status=InstanceStatus.OFFLINE,
            credential_hash=token_hash,
            registered_by=registered_by,
        )
        self.db.add(instance)
        await self.db.flush()
        return instance, token

    async def authenticate(self, instance_id: uuid.UUID, token: str) -> ManagedInstance:
        instance = await self.db.get(ManagedInstance, instance_id)
        if not instance or not verify_instance_credential(token, instance.credential_hash):
            raise ValueError("Invalid instance credentials")
        return instance

    async def heartbeat(
        self,
        instance: ManagedInstance,
        *,
        status: str,
        version: str | None,
        capabilities: list | None,
        metrics: dict | None,
    ) -> InstanceHeartbeat:
        now = datetime.now(UTC)
        instance.last_seen_at = now
        instance.status = status
        if version:
            instance.version = version
        if capabilities is not None:
            instance.capabilities = capabilities

        hb = InstanceHeartbeat(
            instance_id=instance.id,
            status=status,
            version=version,
            capabilities=capabilities or [],
            metrics_snapshot=metrics or {},
        )
        self.db.add(hb)
        record_instance_heartbeat(status=status)
        await self.db.flush()
        return hb

    async def refresh_offline_instances(self, org_id: uuid.UUID | None = None) -> int:
        cutoff = datetime.now(UTC) - timedelta(seconds=HEARTBEAT_STALE_SECONDS)
        q = select(ManagedInstance).where(
            ManagedInstance.last_seen_at.isnot(None),
            ManagedInstance.last_seen_at < cutoff,
            ManagedInstance.status != InstanceStatus.OFFLINE,
        )
        if org_id:
            q = q.where(ManagedInstance.organization_id == org_id)
        result = await self.db.execute(q)
        count = 0
        for inst in result.scalars().all():
            inst.status = InstanceStatus.OFFLINE
            count += 1
        return count

    async def sync_policies(self, instance: ManagedInstance) -> PolicySyncRecord:
        policies = await self.db.execute(
            select(GovernancePolicy).where(
                GovernancePolicy.organization_id == instance.organization_id,
                GovernancePolicy.status == PolicyStatus.ACTIVE,
            )
        )
        active = list(policies.scalars().all())
        policy_version = max((p.version for p in active), default=0)

        record = PolicySyncRecord(
            organization_id=instance.organization_id,
            instance_id=instance.id,
            policy_version=policy_version,
            instance_policy_version=None,
            status=SyncStatus.PENDING,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def report_policy_sync(
        self,
        instance: ManagedInstance,
        *,
        instance_policy_version: int,
        success: bool,
    ) -> PolicySyncRecord:
        record = PolicySyncRecord(
            organization_id=instance.organization_id,
            instance_id=instance.id,
            policy_version=instance_policy_version,
            instance_policy_version=instance_policy_version,
            status=SyncStatus.SYNCED if success else SyncStatus.FAILED,
            last_sync_at=datetime.now(UTC),
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def fleet_overview(self, org_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(ManagedInstance).where(ManagedInstance.organization_id == org_id)
        )
        instances = list(result.scalars().all())
        await self.refresh_offline_instances(org_id)
        by_status: dict[str, int] = {}
        for inst in instances:
            by_status[inst.status] = by_status.get(inst.status, 0) + 1
        return {
            "total_instances": len(instances),
            "by_status": by_status,
            "instances": [
                {
                    "id": str(i.id),
                    "name": i.name,
                    "endpoint": i.endpoint,
                    "status": i.status,
                    "version": i.version,
                    "last_seen_at": i.last_seen_at.isoformat() if i.last_seen_at else None,
                    "capabilities": i.capabilities or [],
                }
                for i in instances
            ],
        }
