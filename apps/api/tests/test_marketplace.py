"""Phase 15 marketplace tests."""

from __future__ import annotations

import pytest

from app.models.extension import PluginType
from app.models.marketplace import MARKETPLACE_CATEGORIES, MarketplaceItemStatus, MarketplaceVisibility
from app.services.marketplace.catalog import MarketplaceCatalogService, slugify, visibility_scope
from app.services.marketplace.validation import run_validation_pipeline, scan_for_secrets, validate_dependencies


class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert slugify("My@Package!") == "my-package"


class TestVisibilityScope:
    def test_public(self):
        assert visibility_scope(MarketplaceVisibility.PUBLIC, None) == "public"

    def test_org(self):
        import uuid

        oid = uuid.uuid4()
        assert visibility_scope(MarketplaceVisibility.ORGANIZATION, oid) == f"org:{oid}"


class TestContentTypeMapping:
    def test_agent_template(self):
        assert MarketplaceCatalogService.content_type_from_plugin(PluginType.AGENT_TEMPLATE.value) == "agent"

    def test_tool(self):
        assert MarketplaceCatalogService.content_type_from_plugin(PluginType.TOOL.value) == "extension"


class TestPackageValidation:
    def test_valid_manifest(self):
        manifest = {
            "name": "test-tool",
            "display_name": "Test Tool",
            "description": "A test tool",
            "version": "1.0.0",
            "plugin_type": "tool",
            "author": "Test",
            "license": "Apache-2.0",
            "minimum_modelbridge_version": "1.0.0",
            "permissions": ["tool_execution"],
            "tool": {"name": "test", "input_schema": {"type": "object"}},
        }
        result = run_validation_pipeline(manifest)
        assert result.valid

    def test_rejects_missing_fields(self):
        result = run_validation_pipeline({"name": "x"})
        assert not result.valid

    def test_detects_secrets(self):
        manifest = {
            "name": "bad-pkg",
            "display_name": "Bad",
            "description": "x",
            "version": "1.0.0",
            "plugin_type": "tool",
            "author": "x",
            "license": "MIT",
            "minimum_modelbridge_version": "1.0.0",
            "api_key": "sk-live-supersecretvalue123",
            "tool": {"name": "t", "input_schema": {"type": "object"}},
        }
        findings = scan_for_secrets(manifest)
        assert len(findings) > 0

    def test_dependency_validation(self):
        errors = validate_dependencies({"dependencies": [{"name": "dep1"}, {"version": 1}]})
        assert len(errors) >= 1


class TestCategories:
    def test_defined(self):
        assert "developer_tools" in MARKETPLACE_CATEGORIES
        assert "security" in MARKETPLACE_CATEGORIES


class TestMarketplaceStatuses:
    def test_status_enum(self):
        assert MarketplaceItemStatus.PUBLISHED == "published"
        assert MarketplaceItemStatus.DRAFT == "draft"
