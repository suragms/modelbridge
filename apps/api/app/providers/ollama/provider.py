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
from app.providers.capabilities import infer_capabilities


class OllamaProvider(AIProvider):
    provider_type = "ollama"

    def __init__(self, api_key: str | None = None, base_url: str | None = None, **kwargs):
        super().__init__(api_key, base_url, **kwargs)
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")

    async def _get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=120.0)

    def _convert_messages(self, messages: list[ChatMessage]) -> list[dict]:
        result = []
        for msg in messages:
            entry: dict = {"role": msg.role}
            if msg.content is not None:
                entry["content"] = msg.content
            if msg.name:
                entry["name"] = msg.name
            result.append(entry)
        return result

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
        async with await self._get_client() as client:
            payload = {
                "model": model,
                "messages": self._convert_messages(messages),
                "stream": False,
            }
            if temperature is not None:
                payload["options"] = payload.get("options", {})
                payload["options"]["temperature"] = temperature
            if top_p is not None:
                payload["options"] = payload.get("options", {})
                payload["options"]["top_p"] = top_p
            if max_tokens is not None:
                payload["options"] = payload.get("options", {})
                payload["options"]["num_predict"] = max_tokens
            if tools:
                payload["tools"] = tools
            if response_format is not None:
                payload["format"] = "json" if response_format.get("type") == "json_object" else None

            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            message = data.get("message", {})
            return ChatCompletionResult(
                id=f"ollama-{uuid.uuid4().hex[:12]}",
                model=model,
                choices=[{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": message.get("content", ""),
                    },
                    "finish_reason": "stop",
                }],
                usage={
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                },
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
        async with await self._get_client() as client:
            payload = {
                "model": model,
                "messages": self._convert_messages(messages),
                "stream": True,
            }
            if temperature is not None:
                payload["options"] = payload.get("options", {})
                payload["options"]["temperature"] = temperature
            if max_tokens is not None:
                payload["options"] = payload.get("options", {})
                payload["options"]["num_predict"] = max_tokens

            chunk_id = f"ollama-{uuid.uuid4().hex[:12]}"

            async with client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    import json
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if data.get("done"):
                        yield StreamChunk(
                            id=chunk_id,
                            model=model,
                            delta={},
                            finish_reason="stop",
                        )
                        return

                    message = data.get("message", {})
                    content = message.get("content", "")
                    if content:
                        yield StreamChunk(
                            id=chunk_id,
                            model=model,
                            delta={"role": "assistant", "content": content},
                            finish_reason=None,
                        )

    async def list_models(self) -> list[ProviderModel]:
        async with await self._get_client() as client:
            try:
                response = await client.get("/api/tags")
                response.raise_for_status()
                data = response.json()

                models = []
                for model in data.get("models", []):
                    name = model.get("name", "")
                    inferred = infer_capabilities(name, "ollama")
                    models.append(ProviderModel(
                        id=name,
                        name=name,
                        context_window=inferred.context_window,
                        supports_chat=inferred.supports_chat,
                        supports_streaming=inferred.supports_streaming,
                        supports_embeddings=inferred.supports_embeddings,
                        supports_tools=inferred.supports_tools,
                        supports_vision=inferred.supports_vision,
                        supports_json_mode=inferred.supports_json_mode,
                    ))
                return models
            except Exception:
                return []

    async def health_check(self) -> bool:
        async with await self._get_client() as client:
            try:
                response = await client.get("/api/tags")
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

        async with await self._get_client() as client:
            embeddings = []
            for text in input_text:
                response = await client.post("/api/embeddings", json={
                    "model": model,
                    "prompt": text,
                })
                response.raise_for_status()
                data = response.json()
                embeddings.append(data.get("embedding", []))

            return EmbeddingResult(
                embeddings=embeddings,
                model=model,
                usage={"prompt_tokens": sum(len(t.split()) for t in input_text), "total_tokens": sum(len(t.split()) for t in input_text)},
            )
