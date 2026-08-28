from __future__ import annotations

from typing import Any, Iterator

from modelbridge._http import HTTPTransport


class ChatCompletions:
    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def create(
        self,
        *,
        model: str,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> dict | Iterator[dict]:
        body: dict[str, Any] = {"model": model, "messages": messages, "stream": stream}
        if temperature is not None:
            body["temperature"] = temperature
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if tools:
            body["tools"] = tools
        body.update(kwargs)

        if stream:
            return self.stream(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, tools=tools, **kwargs)
        return self._transport.request("POST", "/v1/chat/completions", json_body=body)

    def stream(self, **kwargs: Any) -> Iterator[dict]:
        import json

        kwargs["stream"] = True
        body: dict[str, Any] = {
            "model": kwargs.pop("model"),
            "messages": kwargs.pop("messages"),
            "stream": True,
        }
        for key in ("temperature", "max_tokens", "tools"):
            if key in kwargs and kwargs[key] is not None:
                body[key] = kwargs.pop(key)
        body.update(kwargs)

        for chunk in self._transport.stream("POST", "/v1/chat/completions", json_body=body):
            yield json.loads(chunk)


class Chat:
    def __init__(self, transport: HTTPTransport):
        self.completions = ChatCompletions(transport)


class EmbeddingsAPI:
    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def create(self, *, model: str, input: str | list[str]) -> dict:
        return self._transport.request(
            "POST",
            "/v1/embeddings",
            json_body={"model": model, "input": input},
        )


class ModelsAPI:
    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def list(self) -> list[dict]:
        return self._transport.request("GET", "/models/", use_token=True)


class AnalyticsAPI:
    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def overview(self, **params: Any) -> dict:
        return self._transport.request("GET", "/analytics/overview", params=params, use_token=True)


class RequestsAPI:
    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def list(self, **params: Any) -> dict:
        return self._transport.request("GET", "/logs/", params=params, use_token=True)

    def get(self, request_id: str) -> dict:
        return self._transport.request("GET", f"/logs/{request_id}", use_token=True)


class ModelBridge:
    """Synchronous ModelBridge client."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str | None = None,
        token: str | None = None,
        timeout: float = 120.0,
        org_id: str | None = None,
    ):
        self._transport = HTTPTransport(base_url, api_key, token, timeout, org_id)
        self.chat = Chat(self._transport)
        self.embeddings = EmbeddingsAPI(self._transport)
        self.models = ModelsAPI(self._transport)
        self.analytics = AnalyticsAPI(self._transport)
        self.requests = RequestsAPI(self._transport)

    def health(self) -> dict:
        return self._transport.request("GET", "/health", auth=False)
