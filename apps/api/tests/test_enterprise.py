"""Phase 11 enterprise collaboration and fleet tests."""

from __future__ import annotations

from app.services.enterprise.config import safe_diff


class TestConfigDiff:
    def test_safe_diff_detects_changes(self):
        a = {"routing": {"strategy": "auto"}, "limits": {"max_tokens": 1000}}
        b = {"routing": {"strategy": "cheapest"}, "limits": {"max_tokens": 1000}}
        diff = safe_diff(a, b)
        assert "routing" in diff["changed"]

    def test_secrets_redacted_in_diff(self):
        a = {"secrets": {"key": "old"}}
        b = {"secrets": {"key": "new"}}
        diff = safe_diff(a, b)
        assert diff["changed"]["secrets"] == "[REDACTED]"

    def test_added_removed_keys(self):
        a = {"a": 1}
        b = {"b": 2}
        diff = safe_diff(a, b)
        assert "a" in diff["removed"]
        assert "b" in diff["added"]


class TestFleetCredentials:
    def test_credential_roundtrip(self):
        from app.services.enterprise.fleet import generate_instance_credential, verify_instance_credential

        token, token_hash = generate_instance_credential()
        assert verify_instance_credential(token, token_hash)
        assert not verify_instance_credential("wrong", token_hash)


class TestWorkspaceRoles:
    def test_role_rank_order(self):
        from app.models.enterprise import WorkspaceRole
        from app.services.enterprise.access import WORKSPACE_ROLE_RANK

        assert WORKSPACE_ROLE_RANK[WorkspaceRole.ADMIN] > WORKSPACE_ROLE_RANK[WorkspaceRole.MEMBER]
        assert WORKSPACE_ROLE_RANK[WorkspaceRole.VIEWER] < WORKSPACE_ROLE_RANK[WorkspaceRole.MEMBER]


class TestPromotionChain:
    def test_promotion_chain_defined(self):
        from app.services.enterprise.config import PROMOTION_CHAIN
        from app.models.enterprise import EnvironmentKind

        assert PROMOTION_CHAIN[EnvironmentKind.DEVELOPMENT] == EnvironmentKind.STAGING
        assert PROMOTION_CHAIN[EnvironmentKind.STAGING] == EnvironmentKind.PRODUCTION
