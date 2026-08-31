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


class GovernanceAPI:
    """Dashboard governance APIs. Requires an access token (not an API key)."""

    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def policies(self) -> list:
        return self._transport.request("GET", "/governance/policies", use_token=True)

    def get_policy(self, policy_id: str) -> dict:
        return self._transport.request("GET", f"/governance/policies/{policy_id}", use_token=True)

    def events(self, **params: Any) -> list:
        return self._transport.request("GET", "/governance/events", params=params, use_token=True)

    def approvals(self, **params: Any) -> list:
        return self._transport.request("GET", "/governance/approvals", params=params, use_token=True)

    def simulate(self, body: dict) -> dict:
        return self._transport.request("POST", "/governance/simulate", json_body=body, use_token=True)


class AgentsAPI:
    """Agent definition and execution APIs (dashboard token required)."""

    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def list(self) -> list:
        return self._transport.request("GET", "/agents", use_token=True)

    def get(self, agent_id: str) -> dict:
        return self._transport.request("GET", f"/agents/{agent_id}", use_token=True)

    def execute(self, agent_id: str, *, input_text: str | None = None, sync: bool = False, **kwargs: Any) -> dict:
        body: dict[str, Any] = {"sync": sync, **kwargs}
        if input_text is not None:
            body["input_text"] = input_text
        return self._transport.request("POST", f"/agents/{agent_id}/execute", json_body=body, use_token=True)

    def get_execution(self, execution_id: str) -> dict:
        return self._transport.request("GET", f"/agents/executions/{execution_id}", use_token=True)

    def list_executions(self, **params: Any) -> list:
        return self._transport.request("GET", "/agents/executions/list", params=params, use_token=True)

    def cancel_execution(self, execution_id: str, reason: str | None = None) -> dict:
        return self._transport.request(
            "POST",
            f"/agents/executions/{execution_id}/cancel",
            json_body={"reason": reason},
            use_token=True,
        )


class WorkflowsAPI:
    """Workflow orchestration APIs (dashboard token required)."""

    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def list(self) -> list:
        return self._transport.request("GET", "/workflows", use_token=True)

    def execute(self, workflow_id: str, *, sync: bool = False, context: dict | None = None, **kwargs: Any) -> dict:
        body: dict[str, Any] = {"sync": sync, **kwargs}
        if context:
            body["context"] = context
        return self._transport.request("POST", f"/workflows/{workflow_id}/execute", json_body=body, use_token=True)

    def get_execution(self, execution_id: str) -> dict:
        return self._transport.request("GET", f"/workflows/executions/{execution_id}", use_token=True)

    def list_executions(self, **params: Any) -> list:
        return self._transport.request("GET", "/workflows/executions/list", params=params, use_token=True)


class ExtensionsAPI:
    """Extension marketplace APIs (dashboard token required)."""

    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def packages(self, **params: Any) -> list:
        return self._transport.request("GET", "/extensions/packages", params=params, use_token=True)

    def installations(self) -> list:
        return self._transport.request("GET", "/extensions/installations", use_token=True)

    def install(self, package_version_id: str, *, approved_permissions: list[str], enable: bool = False, **kwargs: Any) -> dict:
        body = {
            "package_version_id": package_version_id,
            "approved_permissions": approved_permissions,
            "enable": enable,
            **kwargs,
        }
        return self._transport.request("POST", "/extensions/installations", json_body=body, use_token=True)

    def enable(self, installation_id: str) -> dict:
        return self._transport.request("POST", f"/extensions/installations/{installation_id}/enable", json_body={}, use_token=True)

    def disable(self, installation_id: str) -> dict:
        return self._transport.request("POST", f"/extensions/installations/{installation_id}/disable", json_body={}, use_token=True)


class TemplatesAPI:
    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def list(self, **params: Any) -> list:
        return self._transport.request("GET", "/templates", params=params, use_token=True)

    def apply(self, installation_id: str, parameters: dict | None = None, activate: bool = False) -> dict:
        return self._transport.request(
            "POST",
            f"/templates/installations/{installation_id}/apply",
            json_body={"parameters": parameters or {}, "activate": activate},
            use_token=True,
        )


class EnterpriseAPI:
    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def overview(self) -> dict:
        return self._transport.request("GET", "/enterprise/overview", use_token=True)

    def workspaces(self) -> list:
        return self._transport.request("GET", "/workspaces", use_token=True)

    def projects(self, **params: Any) -> list:
        return self._transport.request("GET", "/projects", params=params, use_token=True)

    def fleet(self) -> dict:
        return self._transport.request("GET", "/fleet", use_token=True)

    def fleet_instance(self, instance_id: str) -> dict:
        return self._transport.request("GET", f"/fleet/{instance_id}", use_token=True)


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
        self.governance = GovernanceAPI(self._transport)
        self.agents = AgentsAPI(self._transport)
        self.workflows = WorkflowsAPI(self._transport)
        self.extensions = ExtensionsAPI(self._transport)
        self.templates = TemplatesAPI(self._transport)
        self.enterprise = EnterpriseAPI(self._transport)

    def health(self) -> dict:
        return self._transport.request("GET", "/health", auth=False)
