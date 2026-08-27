from __future__ import annotations

from app.providers.openai_provider.provider import OpenAIProvider


class LMStudioProvider(OpenAIProvider):
    provider_type = "lmstudio"

    def __init__(self, api_key: str | None = None, base_url: str | None = None, **kwargs):
        super().__init__(api_key, base_url or "http://localhost:1234/v1", **kwargs)
