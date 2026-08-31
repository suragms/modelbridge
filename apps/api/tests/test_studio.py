"""Phase 16 AI Studio tests."""

from __future__ import annotations

import json

import pytest

from app.models.studio import STUDIO_NODE_TYPES
from app.services.studio.evaluations import (
    score_contains,
    score_exact_match,
    score_json_schema,
    score_regex,
)
from app.services.studio.import_export import export_resource, strip_secrets, validate_import
from app.services.studio.prompts import extract_variables, validate_variables
from app.services.studio.workflows import (
    compile_visual_to_engine,
    substitute_prompt_variables,
    validate_visual_workflow,
)


def _valid_visual() -> dict:
    return {
        "nodes": [
            {"id": "trigger-1", "type": "trigger", "config": {}},
            {"id": "model-1", "type": "ai_model", "config": {"model": "auto"}},
            {"id": "output-1", "type": "output", "config": {}},
        ],
        "edges": [
            {"source": "trigger-1", "target": "model-1"},
            {"source": "model-1", "target": "output-1"},
        ],
    }


class TestStudioNodeTypes:
    def test_catalog_includes_required_nodes(self):
        for ntype in ("trigger", "ai_model", "agent", "condition", "output", "approval"):
            assert ntype in STUDIO_NODE_TYPES


class TestVisualWorkflowValidation:
    def test_valid_workflow_passes(self):
        result = validate_visual_workflow(_valid_visual())
        assert result.valid, result.errors

    def test_missing_trigger_fails(self):
        visual = _valid_visual()
        visual["nodes"] = [n for n in visual["nodes"] if n["type"] != "trigger"]
        result = validate_visual_workflow(visual)
        assert not result.valid
        assert any("trigger" in e.lower() for e in result.errors)

    def test_missing_output_fails(self):
        visual = _valid_visual()
        visual["nodes"] = [n for n in visual["nodes"] if n["type"] != "output"]
        result = validate_visual_workflow(visual)
        assert not result.valid

    def test_cycle_detection(self):
        visual = {
            "nodes": [
                {"id": "a", "type": "trigger", "config": {}},
                {"id": "b", "type": "ai_model", "config": {"model": "auto"}},
                {"id": "c", "type": "output", "config": {}},
            ],
            "edges": [
                {"source": "a", "target": "b"},
                {"source": "b", "target": "c"},
                {"source": "c", "target": "b"},
            ],
        }
        result = validate_visual_workflow(visual)
        assert not result.valid
        assert any("cycle" in e.lower() for e in result.errors)

    def test_agent_node_requires_agent_id(self):
        visual = {
            "nodes": [
                {"id": "t", "type": "trigger", "config": {}},
                {"id": "a", "type": "agent", "config": {}},
                {"id": "o", "type": "output", "config": {}},
            ],
            "edges": [{"source": "t", "target": "a"}, {"source": "a", "target": "o"}],
        }
        result = validate_visual_workflow(visual)
        assert not result.valid
        assert any("agent_id" in e for e in result.errors)


class TestWorkflowCompilation:
    def test_compiles_to_engine_nodes(self):
        compiled = compile_visual_to_engine(_valid_visual()["nodes"], _valid_visual()["edges"])
        types = {n["node_type"] for n in compiled}
        assert "start" in types
        assert "terminal" in types
        assert "tool" in types

    def test_condition_branches(self):
        nodes = [
            {"id": "t", "type": "trigger", "config": {}},
            {"id": "c", "type": "condition", "config": {"field": "status"}},
            {"id": "o", "type": "output", "config": {}},
        ]
        edges = [
            {"source": "t", "target": "c"},
            {"source": "c", "target": "o", "sourceHandle": "true"},
        ]
        compiled = compile_visual_to_engine(nodes, edges)
        cond = next(n for n in compiled if n["node_key"] == "c")
        assert cond["next_on_true"] == "o"


class TestPromptVariables:
    def test_extract_variables(self):
        vars_ = extract_variables("Hello {{customer_name}}, welcome to {{product}}")
        names = {v["name"] for v in vars_}
        assert names == {"customer_name", "product"}

    def test_validate_duplicate_variables(self):
        errors = validate_variables([{"name": "x"}, {"name": "x"}])
        assert any("Duplicate" in e for e in errors)

    def test_substitute_rejects_secrets(self):
        content, errors = substitute_prompt_variables("Use {{api_key}}", {"api_key": "secret"})
        assert errors
        assert "{{api_key}}" in content

    def test_substitute_missing_variable(self):
        content, errors = substitute_prompt_variables("Hi {{name}}", {})
        assert errors
        assert "{{name}}" in content

    def test_substitute_success(self):
        content, errors = substitute_prompt_variables("Hi {{name}}", {"name": "Ada"})
        assert not errors
        assert content == "Hi Ada"


class TestEvaluationScorers:
    def test_exact_match(self):
        passed, _ = score_exact_match("hello", "hello")
        assert passed
        passed, _ = score_exact_match("hello", "world")
        assert not passed

    def test_contains(self):
        passed, _ = score_contains("The answer is 42", "42")
        assert passed

    def test_regex(self):
        passed, _ = score_regex("order-12345", r"order-\d+")
        assert passed

    def test_json_schema(self):
        passed, _ = score_json_schema('{"name":"test"}', {"required": ["name"], "properties": {"name": {"type": "string"}}})
        assert passed
        passed, _ = score_json_schema("not json", {"required": ["name"]})
        assert not passed


class TestImportExport:
    def test_strip_secrets(self):
        data = strip_secrets({"name": "wf", "api_key": "sk-test", "nested": {"password": "x"}})
        assert data["api_key"] == "[REDACTED]"
        assert data["nested"]["password"] == "[REDACTED]"
        assert data["name"] == "wf"

    def test_export_format(self):
        payload = export_resource("prompt", {"name": "Test", "content": "Hi"})
        assert payload["format"] == "modelbridge-studio-v1"
        assert payload["resource_type"] == "prompt"

    def test_validate_import_rejects_secrets(self):
        payload = {
            "format": "modelbridge-studio-v1",
            "resource_type": "prompt",
            "data": {"api_key": "sk-live-abc123"},
        }
        errors = validate_import(payload)
        assert any("secret" in e.lower() for e in errors)

    def test_validate_import_requires_format(self):
        errors = validate_import({"resource_type": "prompt", "data": {}})
        assert any("format" in e.lower() for e in errors)
