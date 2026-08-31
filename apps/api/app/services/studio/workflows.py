"""Visual workflow validation and compilation to execution nodes."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.models.studio import STUDIO_NODE_TYPES
from app.services.agents.validation import validate_workflow

STUDIO_TO_ENGINE = {
    "trigger": "start",
    "output": "terminal",
    "agent": "agent",
    "condition": "condition",
    "approval": "approval",
    "webhook": "start",
    "ai_model": "tool",
    "transform": "tool",
    "integration": "tool",
}


@dataclass
class StudioValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_visual_workflow(visual: dict) -> StudioValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    nodes = visual.get("nodes") or []
    edges = visual.get("edges") or []

    if not nodes:
        return StudioValidationResult(False, ["Workflow must have at least one node"])

    node_ids = {n.get("id") for n in nodes}
    if len(node_ids) != len(nodes):
        errors.append("Duplicate node IDs")

    triggers = [n for n in nodes if n.get("type") == "trigger"]
    outputs = [n for n in nodes if n.get("type") == "output"]
    if len(triggers) != 1:
        errors.append("Workflow must have exactly one trigger node")
    if not outputs:
        errors.append("Workflow must have at least one output node")

    for node in nodes:
        ntype = node.get("type")
        nid = node.get("id")
        if ntype not in STUDIO_NODE_TYPES:
            errors.append(f"Unknown node type: {ntype} ({nid})")
        config = node.get("config") or {}
        if ntype == "agent" and not config.get("agent_id"):
            errors.append(f"Agent node {nid} missing agent_id")
        if ntype == "ai_model" and not config.get("model"):
            errors.append(f"AI Model node {nid} missing model")
        if ntype == "condition" and not config.get("field"):
            errors.append(f"Condition node {nid} missing field configuration")

    for edge in edges:
        src = edge.get("source")
        tgt = edge.get("target")
        if src not in node_ids:
            errors.append(f"Edge references unknown source: {src}")
        if tgt not in node_ids:
            errors.append(f"Edge references unknown target: {tgt}")

    # Cycle detection via DFS
    adj: dict[str, list[str]] = {n["id"]: [] for n in nodes}
    for edge in edges:
        if edge.get("source") in adj:
            adj[edge["source"]].append(edge["target"])

    visited: set[str] = set()
    stack: set[str] = set()

    def has_cycle(node: str) -> bool:
        visited.add(node)
        stack.add(node)
        for nxt in adj.get(node, []):
            if nxt not in visited:
                if has_cycle(nxt):
                    return True
            elif nxt in stack:
                return True
        stack.remove(node)
        return False

    for n in nodes:
        if n["id"] not in visited and has_cycle(n["id"]):
            errors.append("Workflow contains invalid cycles")
            break

    if not errors:
        compiled = compile_visual_to_engine(nodes, edges)
        engine_result = validate_workflow(compiled)
        if not engine_result.valid:
            errors.extend(engine_result.errors)

    if not errors and any(n.get("type") == "integration" for n in nodes):
        warnings.append("Integration nodes compile to tool stubs — verify integration is configured")

    return StudioValidationResult(len(errors) == 0, errors, warnings)


def compile_visual_to_engine(nodes: list[dict], edges: list[dict]) -> list[dict]:
    """Compile visual canvas to WorkflowNode-compatible definitions."""
    edge_map: dict[str, dict[str, str]] = {}
    for edge in edges:
        src = edge["source"]
        edge_map.setdefault(src, {})
        handle = edge.get("sourceHandle") or "default"
        edge_map[src][handle] = edge["target"]

    engine_nodes: list[dict] = []
    for i, node in enumerate(nodes):
        ntype = node.get("type", "trigger")
        engine_type = STUDIO_TO_ENGINE.get(ntype, "delay")
        key = node.get("id") or f"node_{i}"
        config = dict(node.get("config") or {})

        if ntype == "ai_model":
            config = {
                "tool_name": "echo",
                "arguments": {"message": f"[ai_model:{config.get('model', 'auto')}]"},
                "_studio_ai_model": config,
            }
        elif ntype == "transform":
            config = {
                "tool_name": "json_format",
                "arguments": config.get("arguments", {}),
            }
        elif ntype == "integration":
            config = {
                "tool_name": "echo",
                "arguments": {"message": f"[integration:{config.get('integration_id', 'unknown')}]"},
            }

        outgoing = edge_map.get(key, {})
        en = {
            "node_key": key,
            "node_type": engine_type,
            "config": config,
            "next_on_success": outgoing.get("default") or outgoing.get("success"),
            "next_on_failure": outgoing.get("failure"),
            "next_on_true": outgoing.get("true"),
            "next_on_false": outgoing.get("false"),
        }
        engine_nodes.append(en)

    return engine_nodes


def substitute_prompt_variables(content: str, variables: dict) -> tuple[str, list[str]]:
    """Replace {{var}} placeholders; never substitute secret-like keys."""
    errors: list[str] = []
    secret_keys = {"password", "secret", "api_key", "token", "credential"}

    def replacer(match: re.Match) -> str:
        name = match.group(1).strip()
        if any(s in name.lower() for s in secret_keys):
            errors.append(f"Cannot substitute secret variable: {name}")
            return match.group(0)
        if name not in variables:
            errors.append(f"Missing variable: {name}")
            return match.group(0)
        return str(variables[name])

    result = re.sub(r"\{\{(\w+)\}\}", replacer, content)
    return result, errors
