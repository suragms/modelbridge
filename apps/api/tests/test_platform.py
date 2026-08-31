"""Phase 14 developer platform tests."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.api_key import ALL_API_KEY_SCOPES, APIKey
from app.services.platform.events import EVENT_CATALOG, EventCatalog, sanitize_event_data
from app.services.platform.signing import generate_webhook_secret, sign_payload, verify_signature
from app.services.platform.ssrf import SSRFError, validate_webhook_url


class TestEventCatalog:
    def test_catalog_has_required_events(self):
        assert "request.completed" in EVENT_CATALOG
        assert "workflow.failed" in EVENT_CATALOG
        assert "anomaly.detected" in EVENT_CATALOG

    def test_list_events_sorted(self):
        types = [e["type"] for e in EventCatalog.list_events()]
        assert types == sorted(types)

    def test_sanitize_strips_secrets(self):
        data = sanitize_event_data({"request_id": "r1", "password": "secret", "api_key": "x"})
        assert data == {"request_id": "r1"}


class TestWebhookSigning:
    def test_sign_and_verify(self):
        secret = generate_webhook_secret()
        payload = b'{"type":"request.completed"}'
        sig = sign_payload(secret, payload)
        assert verify_signature(secret, payload, sig)

    def test_rejects_expired_timestamp(self):
        secret = generate_webhook_secret()
        payload = b"{}"
        old_ts = int(time.time()) - 600
        sig = sign_payload(secret, payload, timestamp=old_ts)
        assert not verify_signature(secret, payload, sig)

    def test_secret_prefix_format(self):
        secret = generate_webhook_secret()
        assert secret.startswith("whsec_")


class TestSSRFProtection:
    def test_blocks_localhost(self):
        with pytest.raises(SSRFError):
            validate_webhook_url("http://localhost/hook")

    def test_blocks_metadata_host(self):
        with pytest.raises(SSRFError):
            validate_webhook_url("https://metadata.google.internal/hook")

    @patch("app.services.platform.ssrf.socket.getaddrinfo")
    def test_blocks_private_ip_resolution(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(None, None, None, None, ("127.0.0.1", 0))]
        with pytest.raises(SSRFError):
            validate_webhook_url("https://example.com/hook")


class TestGitHubWebhookVerification:
    def test_valid_signature(self):
        from app.services.platform.integrations import IntegrationService

        secret = "test-secret"
        payload = b'{"action":"opened"}'
        sig = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert IntegrationService.verify_github_webhook(payload, sig, secret)

    def test_invalid_signature(self):
        from app.services.platform.integrations import IntegrationService

        assert not IntegrationService.verify_github_webhook(b"{}", "sha256=bad", "secret")


class TestAPIKeyScopes:
    def test_platform_scopes_defined(self):
        assert "webhooks:manage" in ALL_API_KEY_SCOPES
        assert "integrations:manage" in ALL_API_KEY_SCOPES
        assert "events:read" in ALL_API_KEY_SCOPES

    def test_scope_enforcement(self):
        key = APIKey(
            key_hash="x",
            key_prefix="mb_abc",
            name="test",
            scopes=["chat:write"],
            user_id=uuid.uuid4(),
        )
        assert key.has_scope("chat:write")
        assert not key.has_scope("webhooks:manage")


class TestCICDAbstraction:
    def test_github_workflow_normalization(self):
        from app.services.platform.cicd import CICDRegistry, PipelineStatus

        raw = {
            "action": "completed",
            "workflow_run": {
                "id": 123,
                "conclusion": "success",
                "head_branch": "main",
                "head_sha": "abc123",
            },
            "repository": {"full_name": "org/repo"},
        }
        event = CICDRegistry.normalize("github", raw)
        assert event is not None
        assert event.status == PipelineStatus.SUCCESS
        assert event.repository == "org/repo"


class TestAutomationTemplates:
    def test_templates_available(self):
        from app.services.platform.automations import AutomationService

        templates = AutomationService.list_templates()
        assert len(templates) >= 3
        ids = {t["id"] for t in templates}
        assert "provider_health_alert" in ids


@pytest.mark.asyncio
async def test_event_bus_emit_validates_type():
    from app.services.platform.events import EventBus

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    bus = EventBus(db)
    result = await bus.emit(
        organization_id=uuid.uuid4(),
        event_type="invalid.event.type",
        data={},
    )
    assert result is None
    db.add.assert_not_called()
