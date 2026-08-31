"""Reference and entry-point tool handlers for extension tools."""

from __future__ import annotations

import logging

from app.plugins.interfaces import ToolPlugin, ToolPluginInfo

logger = logging.getLogger(__name__)

_REFERENCE_HANDLERS: dict[str, ToolPlugin] = {}


async def _hello_handler(args: dict) -> dict:
    name = args.get("name", "world")
    return {"greeting": f"Hello, {name}!"}


class HelloToolPlugin(ToolPlugin):
    info = ToolPluginInfo(
        name="hello",
        description="Returns a greeting (reference extension)",
        input_schema={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
        risk_level="low",
        version="1.0.0",
    )

    async def execute(self, arguments: dict) -> dict:
        return await _hello_handler(arguments)


def register_reference_tool(plugin: ToolPlugin) -> None:
    _REFERENCE_HANDLERS[plugin.info.name] = plugin


def get_reference_tool(name: str) -> ToolPlugin | None:
    return _REFERENCE_HANDLERS.get(name)


def init_reference_tools() -> None:
    register_reference_tool(HelloToolPlugin())


async def execute_extension_tool(name: str, arguments: dict) -> dict:
    plugin = get_reference_tool(name)
    if not plugin:
        raise ValueError(f"Extension tool not loaded: {name}")
    return await plugin.execute(arguments)
