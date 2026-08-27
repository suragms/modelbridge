from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import httpx

from app.providers.base import (
    AIProvider,
    ChatCompletionResult,
    ChatMessage,
    EmbeddingResult,
    ProviderModel,
    StreamChunk,
)


class OpenAIProvider(AIProvider):
    provider_type = "openai"

    def __init__(self, api_key: str | None = None, base_url: str | None = None, **kwargs):
        super().__init__(api_key, base_url, **kwargs)
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")

    def _get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _convert_messages(self, messages: list[ChatMessage]) -> list[dict]:
        result = []
        for msg in messages:
            entry: dict = {"role": msg.role}
            if msg.content is not None:
                entry["content"] = msg.content
            if msg.name:
                entry["name"] = msg.name
            if msg.tool_calls:
                entry["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                entry["tool_call_id"] = msg.tool_call_id
            result.append(entry)
        return result

    def _build_payload(
        self,
        model: str,
        messages: list[ChatMessage],
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
        stop: str | list[str] | None = None,
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
        response_format: dict | None = None,
        **kwargs,
    ) -> dict:
        payload: dict = {
            "model": model,
            "messages": self._convert_messages(messages),
            "stream": stream,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if top_p is not None:
            payload["top_p"] = top_p
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if stop is not None:
            payload["stop"] = stop
        if tools:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if response_format is not None:
            payload["response_format"] = response_format
        return payload

    async def chat_completion(
        self,
        model: str,
        messages: list[ChatMessage],
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
        stop: str | list[str] | None = None,
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
        response_format: dict | None = None,
        **kwargs,
    ) -> ChatCompletionResult:
        payload = self._build_payload(
            model, messages, temperature, top_p, max_tokens, False, stop, tools, tool_choice, response_format
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()

            choices = []
            for choice in data.get("choices", []):
                msg = choice.get("message", {})
                choices.append({
                    "index": choice.get("index", 0),
                    "message": {
                        "role": msg.get("role", "assistant"),
                        "content": msg.get("content", ""),
                        **({"tool_calls": msg["tool_calls"]} if msg.get("tool_calls") else {}),
                    },
                    "finish_reason": choice.get("finish_reason", "stop"),
                })

            usage_data = data.get("usage", {})
            return ChatCompletionResult(
                id=data.get("id", f"openai-{uuid.uuid4().hex[:12]}"),
                model=data.get("model", model),
                choices=choices,
                usage={
                    "prompt_tokens": usage_data.get("prompt_tokens", 0),
                    "completion_tokens": usage_data.get("completion_tokens", 0),
                    "total_tokens": usage_data.get("total_tokens", 0),
                },
                finish_reason=choices[0]["finish_reason"] if choices else "stop",
            )

    async def stream_completion(
        self,
        model: str,
        messages: list[ChatMessage],
        temperature: float | None = None,
        top_p: float | None = None,
        max_tokens: int | None = None,
        stop: str | list[str] | None = None,
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
        response_format: dict | None = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        import json

        payload = self._build_payload(
            model, messages, temperature, top_p, max_tokens, True, stop, tools, tool_choice, response_format
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self._get_headers(),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        return
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    choices = data.get("choices", [])
                    for choice in choices:
                        delta = choice.get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield StreamChunk(
                                id=data.get("id", ""),
                                model=data.get("model", model),
                                delta={"role": "assistant", "content": content},
                                finish_reason=choice.get("finish_reason"),
                            )
                        elif choice.get("finish_reason"):
                            yield StreamChunk(
                                id=data.get("id", ""),
                                model=data.get("model", model),
                                delta={},
                                finish_reason=choice.get("finish_reason"),
                            )

    async def list_models(self) -> list[ProviderModel]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                data = response.json()

                models = []
                for model in data.get("data", []):
                    models.append(ProviderModel(
                        id=model.get("id", ""),
                        name=model.get("id", ""),
                        context_window=4096,
                        supports_streaming=True,
                        supports_tools=True,
                        supports_embeddings="embed" in model.get("id", "").lower(),
                        supports_vision="vision" in model.get("id", "").lower() or "gpt-4" in model.get("id", "").lower(),
                        supports_json_mode=True,
                    ))
                return models
            except Exception:
                return []

    async def health_check(self) -> bool:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self._get_headers(),
                )
                return response.status_code == 200
            except Exception:
                return False

    async def generate_embeddings(
        self,
        model: str,
        input_text: str | list[str],
    ) -> EmbeddingResult:
        if isinstance(input_text, str):
            input_text = [input_text]

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                json={"model": model, "input": input_text},
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()

            embeddings = [item["embedding"] for item in data.get("data", [])]
            usage_data = data.get("usage", {})

            return EmbeddingResult(
                embeddings=embeddings,
                model=data.get("model", model),
                usage={
                    "prompt_tokens": usage_data.get("prompt_tokens", 0),
                    "total_tokens": usage_data.get("total_tokens", 0),
                },
            )
