"""Phase 5 production readiness tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth.rbac import Permission, role_has_permission
from app.main import app
from app.models.api_key import APIKey, DEFAULT_API_KEY_SCOPES
from app.models.organization_member import OrganizationRole
from app.utils.slug import slugify

client = TestClient(app)


class TestRBAC:
    def test_owner_has_all_permissions(self):
        assert role_has_permission(OrganizationRole.OWNER, Permission.ORG_DELETE)
        assert role_has_permission(OrganizationRole.OWNER, Permission.KEYS_MANAGE)

    def test_viewer_cannot_manage_providers(self):
        assert not role_has_permission(OrganizationRole.VIEWER, Permission.PROVIDERS_MANAGE)

    def test_member_can_use_playground(self):
        assert role_has_permission(OrganizationRole.MEMBER, Permission.PLAYGROUND_USE)

    def test_admin_can_manage_routing(self):
        assert role_has_permission(OrganizationRole.ADMIN, Permission.ROUTING_MANAGE)


class TestAPIKeyScopes:
    def test_empty_scopes_default_to_full_access(self):
        key = APIKey(
            key_hash="x",
            key_prefix="mb_...",
            name="test",
            user_id=uuid.uuid4(),
            scopes=[],
        )
        assert key.effective_scopes() == DEFAULT_API_KEY_SCOPES

    def test_custom_scopes(self):
        key = APIKey(
            key_hash="x",
            key_prefix="mb_...",
            name="test",
            user_id=uuid.uuid4(),
            scopes=["chat:write"],
        )
        assert key.has_scope("chat:write")
        assert not key.has_scope("embeddings:write")


class TestSlugify:
    def test_basic_slug(self):
        assert slugify("My Organization") == "my-organization"

    def test_special_chars(self):
        assert slugify("Acme Corp!!!") == "acme-corp"


class TestRateLimitHeaders:
    @pytest.mark.asyncio
    async def test_rate_limit_result_headers(self):
        from app.services.rate_limit import RateLimitResult, rate_limit_headers

        result = RateLimitResult(True, 100, 99, 1234567890)
        headers = rate_limit_headers(result)
        assert headers["X-RateLimit-Limit"] == "100"
        assert headers["X-RateLimit-Remaining"] == "99"
        assert headers["X-RateLimit-Reset"] == "1234567890"


class TestConfigValidation:
    def test_production_rejects_default_jwt(self, monkeypatch):
        from app.config import Settings, validate_production_settings

        monkeypatch.setenv("ENVIRONMENT", "production")
        from app.config import get_settings

        get_settings.cache_clear()
        errors = validate_production_settings()
        assert any("JWT_SECRET" in e for e in errors)
        get_settings.cache_clear()


class TestOrganizationsEndpoint:
    def test_list_orgs_requires_auth(self):
        response = client.get("/organizations/")
        assert response.status_code == 401


class TestGatewayScopes:
    @pytest.mark.asyncio
    async def test_missing_scope_rejected(self):
        from app.services.gateway_guard import enforce_gateway_guards

        key = APIKey(
            key_hash="x",
            key_prefix="mb_...",
            name="limited",
            user_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            scopes=["models:read"],
        )
        user = MagicMock()
        user.organization_id = key.organization_id
        db = AsyncMock()

        with patch("app.services.gateway_guard._get_org_settings", new_callable=AsyncMock) as mock_settings:
            mock_settings.return_value = MagicMock(
                rate_limit_per_minute=1000,
                rate_limit_per_day=100000,
                monthly_token_limit=None,
                monthly_budget_usd=None,
                budget_warning_percent=80,
                budget_hard_limit_percent=100,
            )
            with patch("app.services.gateway_guard.enforce_rate_limits", new_callable=AsyncMock) as mock_rl:
                mock_rl.return_value = {}
                with patch("app.services.gateway_guard.check_token_quota", new_callable=AsyncMock):
                    with patch("app.services.gateway_guard.check_budget", new_callable=AsyncMock):
                        request = MagicMock()
                        request.headers = {}
                        request.client = None
                        with pytest.raises(HTTPException) as exc:
                            await enforce_gateway_guards(
                                request,
                                db,
                                user=user,
                                api_key=key,
                                organization_id=key.organization_id,
                                path="/v1/chat/completions",
                            )
                        assert exc.value.status_code == 403
