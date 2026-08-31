"""Phase 10 extension ecosystem tests."""

from __future__ import annotations

import pytest

from app.services.extensions.manifest import is_compatible, validate_manifest


class TestManifestValidation:
    def test_valid_manifest(self):
        data = {
            "name": "my-tool",
            "display_name": "My Tool",
            "description": "A test tool",
            "version": "1.0.0",
            "plugin_type": "tool",
            "author": "Test",
            "license": "Apache-2.0",
            "minimum_modelbridge_version": "1.0.0",
            "permissions": ["tool_execution"],
            "tool": {
                "name": "my_tool",
                "input_schema": {"type": "object", "properties": {}},
            },
        }
        result = validate_manifest(data)
        assert result.valid

    def test_invalid_name(self):
        result = validate_manifest({
            "name": "INVALID",
            "display_name": "X",
            "description": "X",
            "version": "1.0.0",
            "plugin_type": "tool",
            "author": "X",
            "license": "MIT",
            "minimum_modelbridge_version": "1.0.0",
        })
        assert not result.valid

    def test_invalid_plugin_type(self):
        result = validate_manifest({
            "name": "bad-type",
            "display_name": "X",
            "description": "X",
            "version": "1.0.0",
            "plugin_type": "unknown",
            "author": "X",
            "license": "MIT",
            "minimum_modelbridge_version": "1.0.0",
        })
        assert not result.valid

    def test_unknown_permission(self):
        result = validate_manifest({
            "name": "perm-test",
            "display_name": "X",
            "description": "X",
            "version": "1.0.0",
            "plugin_type": "integration",
            "author": "X",
            "license": "MIT",
            "minimum_modelbridge_version": "1.0.0",
            "permissions": ["superuser_access"],
        })
        assert not result.valid

    def test_template_requires_definition(self):
        result = validate_manifest({
            "name": "tmpl",
            "display_name": "T",
            "description": "T",
            "version": "1.0.0",
            "plugin_type": "agent_template",
            "author": "X",
            "license": "MIT",
            "minimum_modelbridge_version": "1.0.0",
        })
        assert not result.valid


class TestCompatibility:
    def test_compatible(self):
        assert is_compatible("1.0.0", "1.0.0")
        assert is_compatible("1.0.0", "1.2.0")

    def test_incompatible(self):
        assert not is_compatible("2.0.0", "1.0.0")


class TestReferenceTools:
    @pytest.mark.asyncio
    async def test_hello_tool(self):
        from app.services.extensions.tools import HelloToolPlugin, init_reference_tools

        init_reference_tools()
        plugin = HelloToolPlugin()
        result = await plugin.execute({"name": "ModelBridge"})
        assert result["greeting"] == "Hello, ModelBridge!"
