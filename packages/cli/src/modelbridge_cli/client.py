"""HTTP client for CLI commands."""

from __future__ import annotations

from typing import Any, Iterator

import httpx

from modelbridge_cli.config import load_config


class CLIClient:
    def __init__(self):
        cfg = load_config()
        self.base_url = (cfg.get("url") or "http://localhost:8000").rstrip("/")
        self.api_key = cfg.get("api_key")
        self.token = cfg.get("access_token")
        self.org_id = cfg.get("org_id")

    def _auth_headers(self, *, gateway: bool = False, dashboard: bool = False) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if gateway and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif dashboard and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.org_id:
            headers["X-Organization-ID"] = self.org_id
        return headers

    def get(self, path: str, *, dashboard: bool = False, params: dict | None = None, auth: bool = True) -> Any:
        headers = self._auth_headers(dashboard=dashboard) if auth else {}
        with httpx.Client(base_url=self.base_url, timeout=60.0) as client:
            resp = client.get(path, headers=headers, params=params)
            resp.raise_for_status()
            return resp.json() if resp.content else None

    def post(
        self,
        path: str,
        body: dict,
        *,
        gateway: bool = False,
        dashboard: bool = False,
        auth: bool = True,
    ) -> Any:
        headers = self._auth_headers(gateway=gateway, dashboard=dashboard) if auth else {"Content-Type": "application/json"}
        with httpx.Client(base_url=self.base_url, timeout=120.0) as client:
            resp = client.post(path, headers=headers, json=body)
            resp.raise_for_status()
            return resp.json()

    def stream_post(self, path: str, body: dict) -> Iterator[str]:
        headers = self._auth_headers(gateway=True)
        with httpx.Client(base_url=self.base_url, timeout=120.0) as client:
            with client.stream("POST", path, headers=headers, json=body) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line.startswith("data: "):
                        yield line[6:].strip()
