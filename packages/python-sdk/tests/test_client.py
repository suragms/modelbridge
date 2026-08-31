"""Python SDK tests."""

import json

import httpx
import pytest
import respx

from modelbridge import ModelBridge
from modelbridge.exceptions import APIError, AuthenticationError


@respx.mock
def test_chat_completion():
    route = respx.post("http://localhost:8000/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "Hi!"}}],
                "model": "auto",
            },
        )
    )
    client = ModelBridge(base_url="http://localhost:8000", api_key="mb_test_key")
    result = client.chat.completions.create(
        model="auto",
        messages=[{"role": "user", "content": "Hello"}],
    )
    assert result["choices"][0]["message"]["content"] == "Hi!"
    assert route.called


@respx.mock
def test_embeddings():
    respx.post("http://localhost:8000/v1/embeddings").mock(
        return_value=httpx.Response(
            200,
            json={"data": [{"embedding": [0.1, 0.2], "index": 0}], "model": "auto"},
        )
    )
    client = ModelBridge(base_url="http://localhost:8000", api_key="mb_test")
    result = client.embeddings.create(model="auto", input="hello")
    assert len(result["data"][0]["embedding"]) == 2


@respx.mock
def test_auth_error():
    respx.post("http://localhost:8000/v1/chat/completions").mock(return_value=httpx.Response(401))
    client = ModelBridge(base_url="http://localhost:8000", api_key="bad")
    with pytest.raises(AuthenticationError):
        client.chat.completions.create(model="auto", messages=[{"role": "user", "content": "x"}])


@respx.mock
def test_governance_policies_requires_token():
    respx.get("http://localhost:8000/governance/policies").mock(
        return_value=httpx.Response(200, json=[])
    )
    client = ModelBridge(base_url="http://localhost:8000", token="jwt-test")
    assert client.governance.policies() == []
    respx.get("http://localhost:8000/health").mock(
        return_value=httpx.Response(200, json={"status": "healthy", "version": "1.0.0"})
    )
    client = ModelBridge(base_url="http://localhost:8000")
    assert client.health()["status"] == "healthy"
