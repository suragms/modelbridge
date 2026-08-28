"""Phase 4 advanced capabilities tests."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.model import Model
from app.models.provider import Provider, ProviderStatus
from app.providers.capabilities import infer_capabilities
from app.router.engine import RoutingEngine
from app.services.capabilities import (
    detect_chat_capabilities,
    missing_capabilities,
    model_capability_map,
)
from app.services.tool_calls import normalize_message_tool_calls, normalize_tool_call
from app.utils.image_urls import UnsafeImageURLError, validate_image_url

client = TestClient(app)


def _make_model(**kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "provider_model_id": "test-model",
        "display_name": "Test Model",
        "context_window": 4096,
        "input_price_per_1k": 0.01,
        "output_price_per_1k": 0.02,
        "supports_chat": True,
        "supports_streaming": True,
        "supports_tools": False,
        "supports_embeddings": False,
        "supports_vision": False,
        "supports_json_mode": False,
        "supports_structured_output": False,
        "supports_tool_choice": False,
        "is_enabled": True,
        "quality_score": 0.7,
        "provider_id": uuid.uuid4(),
    }
    defaults.update(kwargs)
    return Model(**defaults)


def _make_provider(**kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "name": "test-provider",
        "type": "openai",
        "base_url": "https://api.example.com/v1",
        "status": ProviderStatus.HEALTHY,
        "is_enabled": True,
        "config": {},
    }
    defaults.update(kwargs)
    return Provider(**defaults)


class TestCapabilityDetection:
    def test_tools_requirement(self):
        from app.schemas.chat import ChatCompletionRequest, ChatMessage

        req = ChatCompletionRequest(
            model="auto",
            messages=[ChatMessage(role="user", content="hi")],
            tools=[{"type": "function", "function": {"name": "get_weather", "parameters": {}}}],
        )
        caps = detect_chat_capabilities(req.messages, req.tools, req.tool_choice, req.response_format, False)
        assert "tools" in caps

    def test_vision_from_message_content(self):
        from app.schemas.chat import ChatMessage

        caps = detect_chat_capabilities(
            [ChatMessage(role="user", content=[
                {"type": "text", "text": "describe"},
                {"type": "image_url", "image_url": {"url": "https://example.com/a.png"}},
            ])],
            None, None, None, False,
        )
        assert "vision" in caps

    def test_json_mode_requires_capability(self):
        from app.schemas.chat import ChatMessage

        caps = detect_chat_capabilities(
            [ChatMessage(role="user", content="json")],
            None, None, {"type": "json_object"}, False,
        )
        assert "json_mode" in caps


class TestCapabilityFiltering:
    def test_embedding_model_excluded_from_chat(self):
        engine = RoutingEngine()
        provider = _make_provider()
        chat_model = _make_model(provider_model_id="gpt-4", provider_id=provider.id)
        embed_model = _make_model(
            provider_model_id="text-embedding-3-small",
            supports_chat=False,
            supports_embeddings=True,
            supports_streaming=False,
            provider_id=provider.id,
        )
        decision = engine.route(
            [chat_model, embed_model], [provider], required_capabilities={"chat"}
        )
        assert decision.model.provider_model_id == "gpt-4"

    def test_tools_filter(self):
        engine = RoutingEngine()
        provider = _make_provider()
        tools_model = _make_model(supports_tools=True, supports_tool_choice=True, provider_id=provider.id)
        plain = _make_model(provider_model_id="plain", provider_id=provider.id)
        decision = engine.route(
            [tools_model, plain], [provider], required_capabilities={"tools", "chat"}
        )
        assert decision.model.supports_tools

    def test_missing_capabilities_lists_gaps(self):
        model = _make_model(supports_vision=False)
        missing = missing_capabilities(model, {"vision", "chat"})
        assert "vision" in missing


class TestToolNormalization:
    def test_openai_tool_call_shape(self):
        raw = {
            "id": "call_1",
            "type": "function",
            "function": {"name": "get_weather", "arguments": '{"location":"NYC"}'},
        }
        norm = normalize_tool_call(raw)
        assert norm.name == "get_weather"
        assert "NYC" in norm.arguments

    def test_message_normalization(self):
        msg = normalize_message_tool_calls({
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "fn", "arguments": "{}"}}],
        })
        assert msg["tool_calls"][0]["function"]["name"] == "fn"


class TestImageURLSecurity:
    def test_rejects_private_host(self):
        with pytest.raises(UnsafeImageURLError):
            validate_image_url("https://127.0.0.1/image.png")

    def test_allows_https_public(self):
        assert validate_image_url("https://example.com/image.png").startswith("https://")

    def test_allows_data_uri(self):
        url = "data:image/png;base64,iVBORw0KGgo="
        assert validate_image_url(url) == url


class TestCapabilityInference:
    def test_embedding_model_not_chat(self):
        caps = infer_capabilities("text-embedding-3-small", "openai")
        assert caps.supports_embeddings
        assert not caps.supports_chat

    def test_no_fabricated_tools_for_unknown(self):
        caps = infer_capabilities("unknown-model-xyz", "ollama")
        assert not caps.supports_tools


class TestEmbeddingsEndpoint:
    def test_embeddings_requires_auth(self):
        response = client.post("/v1/embeddings", json={"model": "auto", "input": "hello"})
        assert response.status_code == 401


class TestPlaygroundEndpoint:
    def test_playground_requires_auth(self):
        response = client.post(
            "/playground/chat",
            json={"model": "auto", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert response.status_code == 401
