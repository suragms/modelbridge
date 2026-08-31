"""Role-based access control for organization-scoped resources."""

from __future__ import annotations

from enum import StrEnum

from fastapi import Depends, HTTPException

from app.auth.org_context import OrgContext, get_org_context_with_header
from app.models.organization_member import OrganizationRole


class Permission(StrEnum):
    ORG_MANAGE = "org.manage"
    ORG_DELETE = "org.delete"
    MEMBERS_MANAGE = "members.manage"
    PROVIDERS_MANAGE = "providers.manage"
    ROUTING_MANAGE = "routing.manage"
    KEYS_MANAGE = "keys.manage"
    SETTINGS_MANAGE = "settings.manage"
    ANALYTICS_READ = "analytics.read"
    PLAYGROUND_USE = "playground.use"
    AUDIT_READ = "audit.read"
    GOVERNANCE_READ = "governance.read"
    GOVERNANCE_MANAGE = "governance.manage"
    GOVERNANCE_APPROVE = "governance.approve"
    AGENTS_READ = "agents.read"
    AGENTS_MANAGE = "agents.manage"
    AGENTS_EXECUTE = "agents.execute"
    EXTENSIONS_READ = "extensions.read"
    EXTENSIONS_MANAGE = "extensions.manage"
    ENTERPRISE_READ = "enterprise.read"
    ENTERPRISE_MANAGE = "enterprise.manage"
    FLEET_READ = "fleet.read"
    FLEET_MANAGE = "fleet.manage"


ROLE_PERMISSIONS: dict[OrganizationRole, frozenset[Permission]] = {
    OrganizationRole.OWNER: frozenset(Permission),
    OrganizationRole.ADMIN: frozenset({
        Permission.MEMBERS_MANAGE,
        Permission.PROVIDERS_MANAGE,
        Permission.ROUTING_MANAGE,
        Permission.KEYS_MANAGE,
        Permission.SETTINGS_MANAGE,
        Permission.ANALYTICS_READ,
        Permission.PLAYGROUND_USE,
        Permission.AUDIT_READ,
        Permission.GOVERNANCE_READ,
        Permission.GOVERNANCE_MANAGE,
        Permission.GOVERNANCE_APPROVE,
        Permission.AGENTS_READ,
        Permission.AGENTS_MANAGE,
        Permission.AGENTS_EXECUTE,
        Permission.EXTENSIONS_READ,
        Permission.EXTENSIONS_MANAGE,
        Permission.ENTERPRISE_READ,
        Permission.ENTERPRISE_MANAGE,
        Permission.FLEET_READ,
        Permission.FLEET_MANAGE,
    }),
    OrganizationRole.MEMBER: frozenset({
        Permission.PLAYGROUND_USE,
        Permission.ANALYTICS_READ,
        Permission.KEYS_MANAGE,
        Permission.GOVERNANCE_READ,
        Permission.AGENTS_READ,
        Permission.AGENTS_EXECUTE,
        Permission.EXTENSIONS_READ,
        Permission.ENTERPRISE_READ,
        Permission.FLEET_READ,
    }),
    OrganizationRole.VIEWER: frozenset({
        Permission.ANALYTICS_READ,
        Permission.AUDIT_READ,
        Permission.GOVERNANCE_READ,
        Permission.AGENTS_READ,
        Permission.EXTENSIONS_READ,
        Permission.ENTERPRISE_READ,
        Permission.FLEET_READ,
    }),
}


def role_has_permission(role: OrganizationRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def require_permission(permission: Permission):
    async def _checker(ctx: OrgContext = Depends(get_org_context_with_header)) -> OrgContext:
        if not role_has_permission(ctx.role, permission):
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "FORBIDDEN",
                    "message": f"Role '{ctx.role.value}' lacks permission '{permission.value}'",
                    "type": "authorization_error",
                },
            )
        return ctx

    return _checker
