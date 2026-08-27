from __future__ import annotations

from app.providers.openai_provider.provider import OpenAIProvider


class OpenRouterProvider(OpenAIProvider):
    provider_type = "openrouter"

    def __init__(self, api_key: str | None = None, base_url: str | None = None, **kwargs):
        super().__init__(api_key, base_url or "https://openrouter.ai/api/v1", **kwargs)
