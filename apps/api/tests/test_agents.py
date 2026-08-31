"""Phase 9 agent infrastructure tests."""

from __future__ import annotations

import pytest

from app.services.agents.state import InvalidStateTransition, assert_transition, can_transition
from app.services.agents.tools import execute_builtin, list_builtin_names, validate_tool_input, get_builtin
from app.services.agents.validation import validate_workflow


class TestAgentStateMachine:
    def test_queued_to_running(self):
        assert can_transition("queued", "running")

    def test_running_to_completed(self):
        assert can_transition("running", "completed")

    def test_completed_is_terminal(self):
        assert not can_transition("completed", "running")

    def test_invalid_transition_raises(self):
        with pytest.raises(InvalidStateTransition):
            assert_transition("completed", "running")

    def test_waiting_for_approval_to_running(self):
        assert can_transition("waiting_for_approval", "running")


class TestBuiltinTools:
    def test_list_builtin_tools(self):
        names = list_builtin_names()
        assert "echo" in names
        assert "current_time" in names

    @pytest.mark.asyncio
    async def test_echo_tool(self):
        result = await execute_builtin("echo", {"message": "hello"})
        assert result["echo"] == "hello"

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        with pytest.raises(ValueError):
            await execute_builtin("not_a_tool", {})

    def test_validate_tool_input_missing_field(self):
        tool = get_builtin("echo")
        assert tool is not None
        with pytest.raises(ValueError):
            validate_tool_input(tool, {})


class TestWorkflowValidation:
    def test_valid_simple_workflow(self):
        nodes = [
            {"node_key": "start", "node_type": "start", "next_on_success": "end"},
            {"node_key": "end", "node_type": "terminal", "config": {"result": "done"}},
        ]
        result = validate_workflow(nodes)
        assert result.valid

    def test_missing_start(self):
        nodes = [{"node_key": "end", "node_type": "terminal"}]
        result = validate_workflow(nodes)
        assert not result.valid
        assert any("start" in e for e in result.errors)

    def test_invalid_tool_reference(self):
        nodes = [
            {"node_key": "start", "node_type": "start", "next_on_success": "t1"},
            {
                "node_key": "t1",
                "node_type": "tool",
                "config": {"tool_name": "forbidden_tool"},
                "next_on_success": "end",
            },
            {"node_key": "end", "node_type": "terminal"},
        ]
        result = validate_workflow(nodes, allowed_tools={"echo"})
        assert not result.valid

    def test_unreachable_terminal(self):
        nodes = [
            {"node_key": "start", "node_type": "start", "next_on_success": "orphan"},
            {"node_key": "orphan", "node_type": "delay"},
            {"node_key": "end", "node_type": "terminal"},
        ]
        result = validate_workflow(nodes)
        assert not result.valid
