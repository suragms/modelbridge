from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from modelbridge.exceptions import APIError, AuthenticationError


class AsyncHTTPTransport:
    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        token: str | None = None,
        timeout: float = 120.0,
        org_id: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.token = token
        self.timeout = timeout
        self.org_id = org_id

    def _headers(self, use_token: bool = False) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if use_token and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        else:
            raise AuthenticationError("API key or access token required")
        if self.org_id:
            headers["X-Organization-ID"] = self.org_id
        return headers

    async def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        params: dict | None = None,
        use_token: bool = False,
        auth: bool = True,
    ) -> Any:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            headers = self._headers(use_token=use_token) if auth else {"Content-Type": "application/json"}
            resp = await client.request(
                method,
                path,
                headers=headers,
                json=json_body,
                params=params,
            )
            return self._parse(resp)

    async def stream(self, path: str, json_body: dict) -> AsyncIterator[dict]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                path,
                headers=self._headers(use_token=False),
                json=json_body,
            ) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode()
                    raise APIError(body, resp.status_code)
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        payload = line[6:].strip()
                        if payload == "[DONE]":
                            break
                        yield json.loads(payload)

    def _parse(self, resp: httpx.Response) -> Any:
        if resp.status_code == 401:
            raise AuthenticationError("Unauthorized")
        if resp.status_code >= 400:
            raise APIError(resp.text, resp.status_code)
        if resp.status_code == 204:
            return None
        return resp.json()


class AsyncChatCompletions:
    def __init__(self, transport: AsyncHTTPTransport):
        self._transport = transport

    async def create(self, *, model: str, messages: list[dict], **kwargs: Any) -> dict:
        body = {"model": model, "messages": messages, "stream": False, **kwargs}
        return await self._transport.request("POST", "/v1/chat/completions", json_body=body)

    async def stream(self, *, model: str, messages: list[dict], **kwargs: Any) -> AsyncIterator[dict]:
        body = {"model": model, "messages": messages, "stream": True, **kwargs}
        async for chunk in self._transport.stream("/v1/chat/completions", body):
            yield chunk


class AsyncEmbeddings:
    def __init__(self, transport: AsyncHTTPTransport):
        self._transport = transport

    async def create(self, *, model: str, input: str | list[str]) -> dict:
        return await self._transport.request(
            "POST", "/v1/embeddings", json_body={"model": model, "input": input}
        )


class AsyncChat:
    def __init__(self, transport: AsyncHTTPTransport):
        self.completions = AsyncChatCompletions(transport)


class AsyncGovernanceAPI:
    def __init__(self, transport: AsyncHTTPTransport):
        self._transport = transport

    async def policies(self) -> list:
        return await self._transport.request("GET", "/governance/policies", use_token=True)

    async def events(self, **params: Any) -> list:
        return await self._transport.request("GET", "/governance/events", params=params, use_token=True)

    async def approvals(self, **params: Any) -> list:
        return await self._transport.request("GET", "/governance/approvals", params=params, use_token=True)


class AsyncAgentsAPI:
    def __init__(self, transport: AsyncHTTPTransport):
        self._transport = transport

    async def list(self) -> list:
        return await self._transport.request("GET", "/agents", use_token=True)

    async def execute(self, agent_id: str, **body: Any) -> dict:
        return await self._transport.request("POST", f"/agents/{agent_id}/execute", json_body=body, use_token=True)

    async def get_execution(self, execution_id: str) -> dict:
        return await self._transport.request("GET", f"/agents/executions/{execution_id}", use_token=True)


class AsyncWorkflowsAPI:
    def __init__(self, transport: AsyncHTTPTransport):
        self._transport = transport

    async def list(self) -> list:
        return await self._transport.request("GET", "/workflows", use_token=True)

    async def execute(self, workflow_id: str, **body: Any) -> dict:
        return await self._transport.request("POST", f"/workflows/{workflow_id}/execute", json_body=body, use_token=True)


class AsyncModelBridge:
    """Asynchronous ModelBridge client."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str | None = None,
        token: str | None = None,
        timeout: float = 120.0,
        org_id: str | None = None,
    ):
        self._transport = AsyncHTTPTransport(base_url, api_key, token, timeout, org_id)
        self.chat = AsyncChat(self._transport)
        self.embeddings = AsyncEmbeddings(self._transport)
        self.governance = AsyncGovernanceAPI(self._transport)
        self.agents = AsyncAgentsAPI(self._transport)
        self.workflows = AsyncWorkflowsAPI(self._transport)

    async def health(self) -> dict:
        return await self._transport.request("GET", "/health", auth=False)
