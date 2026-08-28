"""Provider plugin interface — matches the existing provider architecture."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from app.providers.base import AIProvider


@dataclass
class ProviderPluginInfo:
    """Metadata returned by a provider plugin."""

    name: str
    version: str = "0.1.0"
    description: str = ""


class ProviderPlugin(ABC):
    """Stable interface for provider plugins installed by administrators.

    Plugins are trusted extensions — ModelBridge does not execute arbitrary
    untrusted code from remote sources.
    """

    info: ProviderPluginInfo

    @abstractmethod
    def create_provider(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> AIProvider:
        """Return a provider instance compatible with the gateway."""

    def capabilities_for_model(self, model_id: str) -> dict[str, bool]:
        """Optional capability hints for a model id."""
        return {}
