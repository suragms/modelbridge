"""Workflow definition validation."""

from __future__ import annotations

from dataclasses import dataclass, field

VALID_NODE_TYPES = frozenset({
    "start",
    "agent",
    "tool",
    "approval",
    "condition",
    "delay",
    "terminal",
})

MAX_CYCLE_VISITS = 50


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


def _node_map(nodes: list[dict]) -> dict[str, dict]:
    return {n["node_key"]: n for n in nodes}


def _next_keys(node: dict) -> list[str]:
    keys: list[str] = []
    for attr in ("next_on_success", "next_on_failure", "next_on_true", "next_on_false"):
        val = node.get(attr)
        if val:
            keys.append(val)
    return keys


def validate_workflow(nodes: list[dict], allowed_tools: set[str] | None = None) -> ValidationResult:
    errors: list[str] = []
    if not nodes:
        return ValidationResult(False, ["Workflow must have at least one node"])

    by_key = _node_map(nodes)
    if len(by_key) != len(nodes):
        errors.append("Duplicate node_key values")

    starts = [n for n in nodes if n.get("node_type") == "start"]
    terminals = [n for n in nodes if n.get("node_type") == "terminal"]
    if len(starts) != 1:
        errors.append("Workflow must have exactly one start node")
    if not terminals:
        errors.append("Workflow must have at least one terminal node")

    for node in nodes:
        key = node.get("node_key")
        ntype = node.get("node_type")
        if not key:
            errors.append("Node missing node_key")
            continue
        if ntype not in VALID_NODE_TYPES:
            errors.append(f"Invalid node type for {key}: {ntype}")
        for ref in _next_keys(node):
            if ref not in by_key:
                errors.append(f"Node {key} references unknown node {ref}")
        if ntype == "tool":
            tool_name = (node.get("config") or {}).get("tool_name")
            if not tool_name:
                errors.append(f"Tool node {key} missing tool_name")
            elif allowed_tools is not None and tool_name not in allowed_tools:
                errors.append(f"Tool node {key} uses unauthorized tool {tool_name}")

    if errors:
        return ValidationResult(False, errors)

    start_key = starts[0]["node_key"]
    reachable: set[str] = set()
    stack = [start_key]
    while stack:
        current = stack.pop()
        if current in reachable:
            continue
        reachable.add(current)
        node = by_key.get(current)
        if not node:
            continue
        stack.extend(_next_keys(node))

    unreachable = set(by_key) - reachable
    if unreachable:
        errors.append(f"Unreachable nodes: {sorted(unreachable)}")

    terminal_reachable = any(t["node_key"] in reachable for t in terminals)
    if not terminal_reachable:
        errors.append("No terminal node is reachable from start")

    # Cycle detection with visit limit
    visits: dict[str, int] = {}

    def walk(key: str, depth: int) -> None:
        if depth > MAX_CYCLE_VISITS:
            errors.append("Workflow cycle exceeds safe visit limit")
            return
        visits[key] = visits.get(key, 0) + 1
        if visits[key] > MAX_CYCLE_VISITS:
            errors.append(f"Cycle detected at node {key}")
            return
        node = by_key.get(key)
        if not node:
            return
        for nxt in _next_keys(node):
            walk(nxt, depth + 1)

    walk(start_key, 0)

    return ValidationResult(len(errors) == 0, errors)
