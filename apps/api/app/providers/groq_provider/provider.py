from __future__ import annotations

from app.providers.openai_provider.provider import OpenAIProvider


class GroqProvider(OpenAIProvider):
    provider_type = "groq"

    def __init__(self, api_key: str | None = None, base_url: str | None = None, **kwargs):
        super().__init__(api_key, base_url or "https://api.groq.com/openai/v1", **kwargs)
