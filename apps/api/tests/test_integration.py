from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.ollama.provider import OllamaProvider


@pytest.mark.asyncio
async def test_ollama_health_check_success():
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("httpx.AsyncClient") as mock_client:
        instance = AsyncMock()
        instance.get = AsyncMock(return_value=mock_response)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = instance

        provider = OllamaProvider(base_url="http://localhost:11434")
        result = await provider.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_ollama_list_models_empty():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"models": []}

    with patch("httpx.AsyncClient") as mock_client:
        instance = AsyncMock()
        instance.get = AsyncMock(return_value=mock_response)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = instance

        provider = OllamaProvider(base_url="http://localhost:11434")
        models = await provider.list_models()
        assert models == []
