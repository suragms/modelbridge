from __future__ import annotations

from typing import TYPE_CHECKING

from app.providers.custom_provider import CustomProvider
from app.providers.groq_provider import GroqProvider
from app.providers.lmstudio_provider import LMStudioProvider
from app.providers.ollama import OllamaProvider
from app.providers.openai_provider import OpenAIProvider
from app.providers.openrouter_provider import OpenRouterProvider

if TYPE_CHECKING:
    from app.providers.base import AIProvider

PROVIDER_MAP: dict[str, type[AIProvider]] = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "groq": GroqProvider,
    "openrouter": OpenRouterProvider,
    "lmstudio": LMStudioProvider,
    "custom": CustomProvider,
}


class ProviderRegistry:
    def __init__(self):
        self._providers: dict[str, AIProvider] = {}

    def create_provider(
        self,
        provider_type: str,
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs,
    ) -> AIProvider:
        provider_cls = PROVIDER_MAP.get(provider_type)
        if not provider_cls:
            raise ValueError(f"Unknown provider type: {provider_type}")
        return provider_cls(api_key=api_key, base_url=base_url, **kwargs)

    def register_provider(self, name: str, provider: AIProvider) -> None:
        self._providers[name] = provider

    def get_provider(self, name: str) -> AIProvider | None:
        return self._providers.get(name)

    def get_all_providers(self) -> dict[str, AIProvider]:
        return dict(self._providers)

    @staticmethod
    def supported_types() -> list[str]:
        return list(PROVIDER_MAP.keys())


_registry: ProviderRegistry | None = None


def get_provider_registry() -> ProviderRegistry:
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry
