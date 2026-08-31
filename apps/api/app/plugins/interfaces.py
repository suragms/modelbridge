"""Extended plugin interfaces for Phase 10 ecosystem."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from app.plugins.base import ProviderPlugin, ProviderPluginInfo


@dataclass
class ExtensionManifest:
    name: str
    display_name: str
    description: str
    version: str
    plugin_type: str
    author: str
    license: str
    minimum_modelbridge_version: str = "1.0.0"
    permissions: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    homepage: str | None = None
    repository: str | None = None
    configuration_schema: dict | None = None


@dataclass
class ToolPluginInfo:
    name: str
    description: str
    input_schema: dict
    output_schema: dict = field(default_factory=dict)
    risk_level: str = "low"
    version: str = "1.0.0"


class ToolPlugin(ABC):
    """Interface for trusted tool extensions (entry-point loaded only)."""

    info: ToolPluginInfo

    @abstractmethod
    async def execute(self, arguments: dict) -> dict:
        """Execute tool with validated arguments."""


class IntegrationPlugin(ABC):
    """Interface for external integration extensions."""

    info: ExtensionManifest

    async def on_install(self) -> None:
        pass

    async def on_enable(self) -> None:
        pass

    async def on_disable(self) -> None:
        pass

    async def on_uninstall(self) -> None:
        pass


LifecycleHook = Callable[[], Awaitable[None]]

__all__ = [
    "ProviderPlugin",
    "ProviderPluginInfo",
    "ExtensionManifest",
    "ToolPlugin",
    "ToolPluginInfo",
    "IntegrationPlugin",
]
