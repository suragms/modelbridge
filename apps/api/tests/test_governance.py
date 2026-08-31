"""Phase 8 governance: policy engine, detection, redaction, isolation."""

from __future__ import annotations

import uuid

import pytest

from app.services.governance.classifier import classify_request
from app.services.governance.detection import (
    categories_only,
    detect_sensitive,
    has_pii,
    has_secret,
)
from app.services.governance.engine import (
    PolicyRecord,
    candidate_allowed,
    evaluate_policies,
    validate_rules,
)
from app.services.governance.redaction import redact_text, replacement_for
from app.services.governance.risk import classify_risk
from app.services.response_cache import build_chat_cache_key


def _policy(**kwargs) -> PolicyRecord:
    defaults = dict(
        id=str(uuid.uuid4()),
        name="p",
        policy_type="organization",
        status="active",
        priority=100,
        action="allow",
        rules={},
        version=1,
    )
    defaults.update(kwargs)
    return PolicyRecord(**defaults)


class TestPolicyEngine:
    def test_default_allow(self):
        d = evaluate_policies([], {"requested_model": "gpt-4"})
        assert d.action == "allow"

    def test_deny(self):
        d = evaluate_policies(
            [_policy(action="deny", name="block-all")],
            {"requested_model": "gpt-4"},
        )
        assert d.action == "deny"

    def test_warn(self):
        d = evaluate_policies(
            [_policy(action="warn", name="warn")],
            {},
        )
        assert d.action == "warn"

    def test_require_approval(self):
        d = evaluate_policies(
            [_policy(action="require_approval", name="approve-high", rules={"conditions": [{"field": "risk_level", "operator": "equals", "value": "HIGH"}]})],
            {"risk_level": "HIGH"},
        )
        assert d.action == "require_approval"

    def test_deny_overrides_allow_same_priority(self):
        d = evaluate_policies(
            [
                _policy(name="allow", action="allow", priority=10),
                _policy(name="deny", action="deny", priority=10),
            ],
            {},
        )
        assert d.action == "deny"

    def test_org_deny_overrides_api_key_allow(self):
        d = evaluate_policies(
            [
                _policy(name="org-deny", action="deny", policy_type="organization", priority=50),
                _policy(name="key-allow", action="allow", policy_type="api_key", priority=1, rules={"api_key_ids": ["k1"]}),
            ],
            {"api_key_id": "k1"},
        )
        assert d.action == "deny"
        assert d.org_denied is True

    def test_priority_order(self):
        d = evaluate_policies(
            [
                _policy(name="later-deny", action="deny", priority=200, rules={"conditions": [{"field": "risk_level", "operator": "equals", "value": "LOW"}]}),
                _policy(name="first-warn", action="warn", priority=1),
            ],
            {"risk_level": "LOW"},
        )
        assert d.action == "deny"

    def test_condition_in_operator(self):
        d = evaluate_policies(
            [_policy(action="deny", rules={"conditions": [{"field": "requested_model", "operator": "in", "value": ["secret-model"]}]})],
            {"requested_model": "secret-model"},
        )
        assert d.action == "deny"

    def test_invalid_field_rejected(self):
        with pytest.raises(ValueError):
            validate_rules({"conditions": [{"field": "__import__", "operator": "equals", "value": "x"}]})

    def test_no_code_execution_in_rules(self):
        with pytest.raises(ValueError):
            validate_rules({"conditions": [{"field": "risk_level", "operator": "eval", "value": "1"}]})


class TestAllowBlockLists:
    def test_allowlist(self):
        d = evaluate_policies(
            [_policy(policy_type="model", action="allow", rules={"allowed_models": ["gpt-4"]})],
            {},
        )
        ok, _ = candidate_allowed(
            model_id="gpt-4", provider_name="openai", provider_type="openai",
            is_local=False, restrictions=d.restrictions,
        )
        blocked, reason = candidate_allowed(
            model_id="claude", provider_name="anthropic", provider_type="anthropic",
            is_local=False, restrictions=d.restrictions,
        )
        assert ok
        assert not blocked
        assert "allowlist" in (reason or "")

    def test_blocklist(self):
        d = evaluate_policies(
            [_policy(policy_type="model", action="deny", rules={"blocked_models": ["bad-model"]})],
            {},
        )
        ok, reason = candidate_allowed(
            model_id="bad-model", provider_name="x", provider_type="openai",
            is_local=False, restrictions=d.restrictions,
        )
        assert not ok
        assert "blocklisted" in reason

    def test_local_only(self):
        d = evaluate_policies(
            [_policy(policy_type="provider", action="allow", rules={"local_only": True})],
            {},
        )
        cloud_ok, _ = candidate_allowed(
            model_id="gpt-4", provider_name="OpenAI", provider_type="openai",
            is_local=False, restrictions=d.restrictions,
        )
        local_ok, _ = candidate_allowed(
            model_id="llama3", provider_name="Ollama", provider_type="ollama",
            is_local=True, restrictions=d.restrictions,
        )
        assert not cloud_ok
        assert local_ok


class TestDetection:
    def test_email_pii(self):
        dets = detect_sensitive("Contact me at user@example.com please")
        assert has_pii(dets)
        assert "Email" in categories_only(dets)

    def test_secret_not_in_labels_value(self):
        text = "token: ghp_abcdefghijklmnopqrstuvwxyz123456"
        dets = detect_sensitive(text)
        assert has_secret(dets)
        labels = categories_only(dets)
        assert "ghp_" not in str(labels)

    def test_redaction_email(self):
        text = "user@example.com"
        dets = detect_sensitive(text)
        out = redact_text(text, dets, replacement_for)
        assert "user@example.com" not in out
        assert "[EMAIL_REDACTED]" in out

    def test_pem_secret(self):
        dets = detect_sensitive("-----BEGIN PRIVATE KEY-----")
        assert has_secret(dets)


class TestClassification:
    def test_general(self):
        assert classify_request("Hello there").classification == "GENERAL"

    def test_code(self):
        assert classify_request("def foo():\n    return 1").classification == "CODE"

    def test_personal(self):
        r = classify_request("here is my social security number")
        assert r.classification == "PERSONAL_DATA"
        assert r.heuristic is True

    def test_risk_reasons(self):
        risk = classify_risk(classification="PERSONAL_DATA", has_pii=True)
        assert risk.level == "HIGH"
        assert risk.reasons


class TestCacheFingerprint:
    def test_policy_change_changes_key(self):
        messages = [{"role": "user", "content": "Hello"}]
        a = build_chat_cache_key(org_id="o1", model="gpt-4", messages=messages, policy_fingerprint="v1")
        b = build_chat_cache_key(org_id="o1", model="gpt-4", messages=messages, policy_fingerprint="v2")
        assert a != b


class TestRbacGovernance:
    def test_viewer_cannot_manage(self):
        from app.auth.rbac import Permission, role_has_permission
        from app.models.organization_member import OrganizationRole

        assert role_has_permission(OrganizationRole.VIEWER, Permission.GOVERNANCE_READ)
        assert not role_has_permission(OrganizationRole.VIEWER, Permission.GOVERNANCE_MANAGE)
        assert not role_has_permission(OrganizationRole.MEMBER, Permission.GOVERNANCE_APPROVE)
        assert role_has_permission(OrganizationRole.ADMIN, Permission.GOVERNANCE_APPROVE)
