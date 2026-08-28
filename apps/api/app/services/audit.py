from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.user import User

# Audit action constants
AUDIT_USER_LOGIN = "user.login"
AUDIT_PROVIDER_CREATED = "provider.created"
AUDIT_PROVIDER_UPDATED = "provider.updated"
AUDIT_PROVIDER_DELETED = "provider.deleted"
AUDIT_PROVIDER_ENABLED = "provider.enabled"
AUDIT_PROVIDER_DISABLED = "provider.disabled"
AUDIT_API_KEY_CREATED = "api_key.created"
AUDIT_API_KEY_REVOKED = "api_key.revoked"
AUDIT_ROUTING_POLICY_CREATED = "routing_policy.created"
AUDIT_ROUTING_POLICY_UPDATED = "routing_policy.updated"


_SENSITIVE_KEYS = frozenset({
    "password", "api_key", "secret", "token", "encrypted_key", "key_hash",
    "authorization", "credential",
})


def _sanitize_metadata(metadata: dict | None) -> dict | None:
    if not metadata:
        return None
    safe: dict = {}
    for key, value in metadata.items():
        if any(s in key.lower() for s in _SENSITIVE_KEYS):
            safe[key] = "[REDACTED]"
        elif isinstance(value, dict):
            safe[key] = _sanitize_metadata(value)
        else:
            safe[key] = value
    return safe


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        actor: User | None = None,
        metadata: dict | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_id=actor.id if actor else None,
            actor_email=actor.email if actor else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_=_sanitize_metadata(metadata),
            organization_id=organization_id or (actor.organization_id if actor else None),
            created_at=datetime.now(UTC),
        )
        self.db.add(entry)
        await self.db.flush()
        return entry
