
import pytest

from app.providers.base import ChatMessage
from app.providers.groq_provider.provider import GroqProvider
from app.providers.ollama.provider import OllamaProvider
from app.providers.openai_provider.provider import OpenAIProvider


class TestOllamaProvider:
    def setup_method(self):
        self.provider = OllamaProvider(base_url="http://localhost:11434")

    def test_provider_type(self):
        assert self.provider.provider_type == "ollama"

    def test_convert_messages(self):
        messages = [
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there"),
        ]
        result = self.provider._convert_messages(messages)
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello"
        assert result[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        provider = OllamaProvider(base_url="http://localhost:99999")
        result = await provider.health_check()
        assert result is False


class TestOpenAIProvider:
    def setup_method(self):
        self.provider = OpenAIProvider(api_key="test-key")

    def test_provider_type(self):
        assert self.provider.provider_type == "openai"

    def test_get_headers(self):
        headers = self.provider._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-key"

    def test_build_payload(self):
        messages = [ChatMessage(role="user", content="Hello")]
        payload = self.provider._build_payload(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=100,
        )
        assert payload["model"] == "gpt-4"
        assert payload["messages"][0]["role"] == "user"
        assert payload["temperature"] == 0.7
        assert payload["max_tokens"] == 100
        assert payload["stream"] is False


class TestGroqProvider:
    def test_provider_type(self):
        provider = GroqProvider(api_key="test-key")
        assert provider.provider_type == "groq"

    def test_base_url(self):
        provider = GroqProvider(api_key="test-key")
        assert "groq.com" in provider.base_url
