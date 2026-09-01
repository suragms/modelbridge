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


class CloudAPI:
    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def health(self) -> dict:
        return self._transport.request("GET", "/cloud/health", use_token=True)

    def regions(self) -> list:
        return self._transport.request("GET", "/cloud/regions", use_token=True)

    def instances(self) -> list:
        return self._transport.request("GET", "/cloud/instances", use_token=True)

    def instance(self, instance_id: str) -> dict:
        return self._transport.request("GET", f"/cloud/instances/{instance_id}", use_token=True)

    def rollouts(self) -> list:
        return self._transport.request("GET", "/cloud/rollouts", use_token=True)

    def onboarding(self) -> dict:
        return self._transport.request("GET", "/cloud/onboarding", use_token=True)


class UsageAPI:
    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def summary(self) -> dict:
        return self._transport.request("GET", "/usage/summary", use_token=True)

    def quotas(self) -> list:
        return self._transport.request("GET", "/quotas", use_token=True)


class IntelligenceAPI:
    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def overview(self) -> dict:
        return self._transport.request("GET", "/intelligence/overview", use_token=True)

    def providers(self, **params: Any) -> dict:
        return self._transport.request("GET", "/intelligence/providers", params=params, use_token=True)

    def costs(self, **params: Any) -> dict:
        return self._transport.request("GET", "/intelligence/costs", params=params, use_token=True)

    def capacity(self) -> dict:
        return self._transport.request("GET", "/intelligence/capacity", use_token=True)

    def anomalies(self) -> list:
        return self._transport.request("GET", "/intelligence/anomalies", use_token=True)

    def recommendations(self, **params: Any) -> list:
        return self._transport.request("GET", "/intelligence/recommendations", params=params, use_token=True)

    def ask(self, question: str) -> dict:
        return self._transport.request(
            "POST", "/operations-assistant/query", json_body={"question": question}, use_token=True
        )


class EventsAPI:
    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def list(self, **params: Any) -> list:
        return self._transport.request("GET", "/events", params=params, use_token=True)

    def catalog(self) -> list:
        return self._transport.request("GET", "/events/catalog", use_token=True)

    def get(self, event_id: str) -> dict:
        return self._transport.request("GET", f"/events/{event_id}", use_token=True)


class WebhooksAPI:
    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def list(self) -> list:
        return self._transport.request("GET", "/webhooks", use_token=True)

    def create(self, *, name: str, url: str, event_types: list[str]) -> dict:
        return self._transport.request(
            "POST", "/webhooks", json_body={"name": name, "url": url, "event_types": event_types}, use_token=True
        )

    def deliveries(self, webhook_id: str) -> list:
        return self._transport.request("GET", f"/webhooks/{webhook_id}/deliveries", use_token=True)


class IntegrationsAPI:
    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def list(self) -> list:
        return self._transport.request("GET", "/integrations", use_token=True)

    def create(self, *, provider: str, name: str, config: dict | None = None) -> dict:
        return self._transport.request(
            "POST", "/integrations", json_body={"provider": provider, "name": name, "config": config or {}}, use_token=True
        )

    def connect(self, integration_id: str, credential: str) -> dict:
        return self._transport.request(
            "POST", f"/integrations/{integration_id}/connect", json_body={"credential": credential}, use_token=True
        )


class AutomationsAPI:
    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def list(self) -> list:
        return self._transport.request("GET", "/automations", use_token=True)

    def templates(self) -> list:
        return self._transport.request("GET", "/automations/templates", use_token=True)

    def execute(self, automation_id: str, *, force: bool = False, context: dict | None = None) -> dict:
        return self._transport.request(
            "POST",
            f"/automations/{automation_id}/execute",
            json_body={"force": force, "context": context or {}},
            use_token=True,
        )


class StudioAPI:
    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def overview(self) -> dict:
        return self._transport.request("GET", "/studio/overview", use_token=True)

    def list_workflows(self) -> list:
        return self._transport.request("GET", "/studio/workflows", use_token=True)

    def create_workflow(self, *, name: str, visual_definition: dict, description: str | None = None) -> dict:
        body: dict[str, Any] = {"name": name, "visual_definition": visual_definition}
        if description:
            body["description"] = description
        return self._transport.request("POST", "/studio/workflows", json_body=body, use_token=True)

    def publish_workflow(self, workflow_id: str) -> dict:
        return self._transport.request("POST", f"/studio/workflows/{workflow_id}/publish", use_token=True)

    def list_agents(self) -> list:
        return self._transport.request("GET", "/studio/agents", use_token=True)

    def compare(self, *, messages: list[dict], models: list[str], **kwargs: Any) -> dict:
        body: dict[str, Any] = {"messages": messages, "models": models, **kwargs}
        return self._transport.request("POST", "/studio/compare", json_body=body, use_token=True)

    def list_deployments(self) -> list:
        return self._transport.request("GET", "/studio/deployments", use_token=True)


class PromptsAPI:
    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def list(self) -> list:
        return self._transport.request("GET", "/prompts/", use_token=True)

    def create(self, *, name: str, content: str, **kwargs: Any) -> dict:
        body: dict[str, Any] = {"name": name, "content": content, **kwargs}
        return self._transport.request("POST", "/prompts/", json_body=body, use_token=True)

    def test(self, prompt_id: str, *, input: str, **kwargs: Any) -> dict:
        body: dict[str, Any] = {"input": input, **kwargs}
        return self._transport.request("POST", f"/prompts/{prompt_id}/test", json_body=body, use_token=True)


class EvaluationsAPI:
    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def list(self) -> list:
        return self._transport.request("GET", "/evaluations/", use_token=True)

    def list_datasets(self) -> list:
        return self._transport.request("GET", "/evaluations/datasets", use_token=True)

    def run(self, suite_id: str) -> dict:
        return self._transport.request("POST", f"/evaluations/{suite_id}/run", use_token=True)

    def get_run(self, run_id: str) -> dict:
        return self._transport.request("GET", f"/evaluation-runs/{run_id}", use_token=True)


class QualityAPI:
    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def overview(self) -> dict:
        return self._transport.request("GET", "/quality/overview", use_token=True)

    def list_pipelines(self) -> list:
        return self._transport.request("GET", "/quality/pipelines", use_token=True)

    def create_pipeline(self, body: dict) -> dict:
        return self._transport.request("POST", "/quality/pipelines", json_body=body, use_token=True)

    def run_pipeline(self, pipeline_id: str) -> dict:
        return self._transport.request("POST", f"/quality/pipelines/{pipeline_id}/run", use_token=True)

    def list_regressions(self) -> list:
        return self._transport.request("GET", "/quality/regressions", use_token=True)

    def compare_regressions(self, body: dict) -> dict:
        return self._transport.request("POST", "/quality/regressions/compare", json_body=body, use_token=True)

    def list_scorecards(self) -> list:
        return self._transport.request("GET", "/quality/scorecards", use_token=True)

    def list_gates(self) -> list:
        return self._transport.request("GET", "/quality/gates", use_token=True)

    def create_gate(self, body: dict) -> dict:
        return self._transport.request("POST", "/quality/gates", json_body=body, use_token=True)


class MarketplaceAPI:
    def __init__(self, transport: HTTPTransport):
        self._transport = transport

    def discovery(self) -> dict:
        return self._transport.request("GET", "/marketplace/discovery", use_token=True)

    def search(self, **params: Any) -> list:
        return self._transport.request("GET", "/marketplace/items", params=params, use_token=True)

    def get(self, slug: str) -> dict:
        return self._transport.request("GET", f"/marketplace/items/{slug}", use_token=True)

    def install(self, item_id: str, *, approved_permissions: list[str], enable: bool = True) -> dict:
        return self._transport.request(
            "POST",
            f"/marketplace/items/{item_id}/install",
            json_body={"approved_permissions": approved_permissions, "enable": enable},
            use_token=True,
        )

    def publish(self, manifest: dict, *, publisher_slug: str, publisher_name: str) -> dict:
        return self._transport.request(
            "POST",
            "/marketplace/items",
            json_body={
                "manifest": manifest,
                "publisher_slug": publisher_slug,
                "publisher_name": publisher_name,
            },
            use_token=True,
        )


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
        self.cloud = CloudAPI(self._transport)
        self.usage = UsageAPI(self._transport)
        self.intelligence = IntelligenceAPI(self._transport)
        self.events = EventsAPI(self._transport)
        self.webhooks = WebhooksAPI(self._transport)
        self.integrations = IntegrationsAPI(self._transport)
        self.automations = AutomationsAPI(self._transport)
        self.marketplace = MarketplaceAPI(self._transport)
        self.studio = StudioAPI(self._transport)
        self.prompts = PromptsAPI(self._transport)
        self.evaluations = EvaluationsAPI(self._transport)
        self.quality = QualityAPI(self._transport)

    def health(self) -> dict:
        return self._transport.request("GET", "/health", auth=False)
