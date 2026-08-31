"""Secure built-in tool registry — no arbitrary code execution."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Awaitable


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    risk_level: str
    handler: Callable[[dict], Awaitable[dict]]


BUILTIN_TOOLS: dict[str, ToolDefinition] = {}


def _register(tool: ToolDefinition) -> None:
    BUILTIN_TOOLS[tool.name] = tool


async def _echo(args: dict) -> dict:
    return {"echo": args.get("message", "")}


async def _current_time(_args: dict) -> dict:
    return {"utc": datetime.now(UTC).isoformat()}


async def _json_format(args: dict) -> dict:
    raw = args.get("data")
    if isinstance(raw, str):
        parsed = json.loads(raw)
    else:
        parsed = raw
    return {"formatted": json.dumps(parsed, indent=2, default=str)}


_register(
    ToolDefinition(
        name="echo",
        description="Echo a message back (safe test tool)",
        input_schema={
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
        output_schema={"type": "object"},
        risk_level="low",
        handler=_echo,
    )
)
_register(
    ToolDefinition(
        name="current_time",
        description="Return current UTC timestamp",
        input_schema={"type": "object", "properties": {}},
        output_schema={"type": "object"},
        risk_level="low",
        handler=_current_time,
    )
)
_register(
    ToolDefinition(
        name="json_format",
        description="Pretty-print JSON data",
        input_schema={
            "type": "object",
            "properties": {"data": {}},
            "required": ["data"],
        },
        output_schema={"type": "object"},
        risk_level="low",
        handler=_json_format,
    )
)


def validate_tool_input(tool: ToolDefinition, arguments: dict) -> None:
    schema = tool.input_schema or {}
    required = schema.get("required") or []
    for field in required:
        if field not in arguments:
            raise ValueError(f"Missing required field: {field}")
    props = schema.get("properties") or {}
    for key, value in arguments.items():
        if key not in props:
            continue
        expected = props[key].get("type")
        if expected == "string" and not isinstance(value, str):
            raise ValueError(f"Field {key} must be a string")
        if expected == "object" and not isinstance(value, dict):
            raise ValueError(f"Field {key} must be an object")


def get_builtin(name: str) -> ToolDefinition | None:
    return BUILTIN_TOOLS.get(name)


def list_builtin_names() -> list[str]:
    return sorted(BUILTIN_TOOLS.keys())


def risk_requires_approval(risk_level: str) -> bool:
    return risk_level in {"high", "critical"}


async def execute_builtin(name: str, arguments: dict) -> dict:
    tool = get_builtin(name)
    if not tool:
        raise ValueError(f"Unknown builtin tool: {name}")
    validate_tool_input(tool, arguments)
    return await tool.handler(arguments)
