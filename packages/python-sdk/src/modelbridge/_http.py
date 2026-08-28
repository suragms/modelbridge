from __future__ import annotations

import json
from typing import Any, Iterator

import httpx

from modelbridge.exceptions import APIError, AuthenticationError


class HTTPTransport:
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

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        params: dict | None = None,
        use_token: bool = False,
        auth: bool = True,
    ) -> Any:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            headers = self._headers(use_token=use_token) if auth else {"Content-Type": "application/json"}
            resp = client.request(
                method,
                path,
                headers=headers,
                json=json_body,
                params=params,
            )
            return self._parse(resp)

    def stream(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
    ) -> Iterator[str]:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            with client.stream(
                method,
                path,
                headers=self._headers(use_token=False),
                json=json_body,
            ) as resp:
                if resp.status_code >= 400:
                    body = resp.read().decode()
                    raise APIError(body, resp.status_code)
                for line in resp.iter_lines():
                    if line.startswith("data: "):
                        payload = line[6:].strip()
                        if payload == "[DONE]":
                            break
                        yield payload

    def _parse(self, resp: httpx.Response) -> Any:
        if resp.status_code == 401:
            raise AuthenticationError("Unauthorized — check API key or token")
        if resp.status_code >= 400:
            detail = resp.text
            try:
                data = resp.json()
                detail = data.get("detail", detail)
                if isinstance(detail, dict):
                    detail = detail.get("message", str(detail))
            except Exception:
                pass
            raise APIError(str(detail), resp.status_code)
        if resp.status_code == 204:
            return None
        return resp.json()
