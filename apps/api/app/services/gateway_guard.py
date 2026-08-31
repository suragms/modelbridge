"""Pre-request gateway guards: scopes, rate limits, quotas, budgets."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey
from app.models.organization_settings import OrganizationSettings
from app.models.user import User
from app.services.budgets import check_budget
from app.services.quotas import check_token_quota
from app.services.rate_limit import enforce_rate_limits
from app.services.token_estimator import estimate_message_tokens


ENDPOINT_SCOPES = {
    "/v1/chat/completions": "chat:write",
    "/v1/embeddings": "embeddings:write",
}


async def _get_org_settings(db: AsyncSession, org_id: uuid.UUID) -> OrganizationSettings:
    result = await db.execute(
        select(OrganizationSettings).where(OrganizationSettings.organization_id == org_id)
    )
    settings = result.scalar_one_or_none()
    if settings:
        return settings
    settings = OrganizationSettings(organization_id=org_id)
    db.add(settings)
    await db.flush()
    return settings


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


async def enforce_gateway_guards(
    request: Request,
    db: AsyncSession,
    *,
    user: User | None,
    api_key: APIKey | None,
    organization_id: uuid.UUID | None,
    path: str,
    messages=None,
    input_text: str | None = None,
) -> dict[str, str]:
    """Validate scope, rate limits, quotas, and budgets before gateway execution."""
    required_scope = ENDPOINT_SCOPES.get(path)
    if api_key and required_scope and not api_key.has_scope(required_scope):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "SCOPE_NOT_ALLOWED",
                "message": f"API key lacks required scope: {required_scope}",
                "type": "authorization_error",
            },
        )

    if api_key and api_key.expires_at:
        from datetime import UTC, datetime

        if api_key.expires_at < datetime.now(UTC):
            raise HTTPException(status_code=401, detail="API key expired")

    org_id = organization_id or (api_key.organization_id if api_key else user.organization_id if user else None)
    if not org_id:
        return {}

    settings = await _get_org_settings(db, org_id)
    headers = await enforce_rate_limits(
        org_id=str(org_id),
        api_key_id=str(api_key.id) if api_key else None,
        user_id=str(user.id) if user and not api_key else None,
        client_ip=_client_ip(request),
        per_minute=settings.rate_limit_per_minute,
        per_day=settings.rate_limit_per_day,
    )

    estimated_tokens = 1
    if messages:
        estimated_tokens = max(1, estimate_message_tokens(messages)[0])
    elif input_text:
        estimated_tokens = max(1, len(input_text) // 4)

    await check_token_quota(
        db,
        organization_id=org_id,
        api_key_id=api_key.id if api_key else None,
        org_monthly_limit=settings.monthly_token_limit,
        key_monthly_limit=api_key.monthly_token_limit if api_key else None,
        estimated_tokens=estimated_tokens,
    )

    await check_budget(
        db,
        organization_id=org_id,
        api_key_id=api_key.id if api_key else None,
        org_budget_usd=settings.monthly_budget_usd,
        key_budget_usd=api_key.monthly_budget_usd if api_key else None,
        warning_percent=settings.budget_warning_percent,
        hard_limit_percent=settings.budget_hard_limit_percent,
    )

    if api_key:
        from datetime import UTC, datetime

        api_key.last_used_at = datetime.now(UTC)
        client_ip = _client_ip(request)
        if client_ip:
            api_key.last_used_ip = client_ip[:45]

    return headers
