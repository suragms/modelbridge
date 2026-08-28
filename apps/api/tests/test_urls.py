import pytest

from app.utils.urls import InvalidURLError, validate_provider_url


class TestValidateProviderUrl:
    def test_none_or_blank_returns_none(self):
        assert validate_provider_url(None, "openai") is None
        assert validate_provider_url("", "openai") is None
        assert validate_provider_url("   ", "openai") is None

    def test_valid_public_url(self):
        result = validate_provider_url("https://api.openai.com/v1", "openai")
        assert result == "https://api.openai.com/v1"

    def test_http_allowed(self):
        result = validate_provider_url("http://localhost:11434", "ollama")
        assert result == "http://localhost:11434"

    def test_rejects_non_http_scheme(self):
        with pytest.raises(InvalidURLError):
            validate_provider_url("ftp://example.com", "openai")

    def test_rejects_embedded_credentials(self):
        with pytest.raises(InvalidURLError):
            validate_provider_url("https://user:pass@api.example.com/v1", "openai")

    def test_rejects_missing_host(self):
        with pytest.raises(InvalidURLError):
            validate_provider_url("https://", "openai")

    def test_rejects_control_characters(self):
        with pytest.raises(InvalidURLError):
            validate_provider_url("https://api.example.com/v1\r\nHost: evil", "openai")

    def test_local_allowed_for_ollama(self):
        result = validate_provider_url("http://localhost:11434", "ollama")
        assert result is not None

    def test_private_ip_blocks_cloud_type(self):
        with pytest.raises(InvalidURLError):
            validate_provider_url("http://127.0.0.1:5000", "openai")
        with pytest.raises(InvalidURLError):
            validate_provider_url("http://192.168.1.10/v1", "openai")

    def test_private_ip_allowed_for_openai_compatible_custom(self):
        # LM Studio / custom OpenAI-compatible servers legitimately run locally.
        result = validate_provider_url("http://127.0.0.1:1234/v1", "lmstudio")
        assert result is not None

    def test_trailing_slash_stripped(self):
        result = validate_provider_url("https://api.example.com/v1/", "openai")
        assert result == "https://api.example.com/v1"
