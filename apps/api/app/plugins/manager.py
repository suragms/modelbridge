"""Plugin discovery, validation, and lifecycle management."""

from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING

from app.plugins.base import ProviderPlugin

if TYPE_CHECKING:
    from app.providers.base import AIProvider

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "modelbridge.providers"


class PluginLoadError(Exception):
    pass


class PluginManager:
    """Discover and manage trusted provider plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, ProviderPlugin] = {}
        self._errors: dict[str, str] = {}

    @property
    def errors(self) -> dict[str, str]:
        return dict(self._errors)

    def discover(self) -> None:
        """Load plugins from setuptools entry points."""
        try:
            from importlib.metadata import entry_points
        except ImportError:
            from importlib_metadata import entry_points  # type: ignore

        eps = entry_points()
        group = eps.select(group=ENTRY_POINT_GROUP) if hasattr(eps, "select") else eps.get(ENTRY_POINT_GROUP, [])

        for ep in group:
            name = ep.name
            try:
                plugin_cls = ep.load()
                plugin = plugin_cls() if callable(plugin_cls) else plugin_cls
                self._validate_plugin(name, plugin)
                self._plugins[name] = plugin
                logger.info("plugin_loaded", name=name, version=getattr(plugin.info, "version", "?"))
            except Exception as e:
                msg = str(e)
                self._errors[name] = msg
                logger.warning("plugin_load_failed", name=name, error=msg)

    def _validate_plugin(self, name: str, plugin: object) -> None:
        if not isinstance(plugin, ProviderPlugin):
            raise PluginLoadError(f"Plugin '{name}' must implement ProviderPlugin")
        if not getattr(plugin, "info", None):
            raise PluginLoadError(f"Plugin '{name}' missing info metadata")

    def register(self, name: str, plugin: ProviderPlugin) -> None:
        self._validate_plugin(name, plugin)
        self._plugins[name] = plugin

    def get(self, name: str) -> ProviderPlugin | None:
        return self._plugins.get(name)

    def create_provider(
        self,
        provider_type: str,
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs,
    ) -> AIProvider | None:
        plugin = self._plugins.get(provider_type)
        if not plugin:
            return None
        return plugin.create_provider(api_key=api_key, base_url=base_url, **kwargs)

    def supported_types(self) -> list[str]:
        return list(self._plugins.keys())

    def diagnostics(self) -> list[dict]:
        out = []
        for name, plugin in self._plugins.items():
            out.append({
                "name": name,
                "version": plugin.info.version,
                "description": plugin.info.description,
                "status": "enabled",
            })
        for name, error in self._errors.items():
            out.append({"name": name, "status": "failed", "error": error})
        return out


_manager: PluginManager | None = None


def get_plugin_manager() -> PluginManager:
    global _manager
    if _manager is None:
        _manager = PluginManager()
        _manager.discover()
    return _manager
