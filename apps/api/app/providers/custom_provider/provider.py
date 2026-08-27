from __future__ import annotations

from app.providers.openai_provider.provider import OpenAIProvider


class CustomProvider(OpenAIProvider):
    """Custom OpenAI-compatible provider. Base URL must be configured."""
    provider_type = "custom"

    def __init__(self, api_key: str | None = None, base_url: str | None = None, **kwargs):
        if not base_url:
            raise ValueError("Custom provider requires a base_url")
        super().__init__(api_key, base_url, **kwargs)
