"""ModelBridge CLI entry point."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from modelbridge_cli import __version__
from modelbridge_cli.client import CLIClient
from modelbridge_cli.config import clear_config, get, load_config, save_config, set_value, show_config

app = typer.Typer(
    name="modelbridge",
    help="Official ModelBridge CLI — manage and interact with your AI gateway.",
    no_args_is_help=True,
)
config_app = typer.Typer(help="Manage CLI configuration")
providers_app = typer.Typer(help="Provider commands")
models_app = typer.Typer(help="Model commands")
analytics_app = typer.Typer(help="Analytics commands")
requests_app = typer.Typer(help="Request log commands")
org_app = typer.Typer(help="Organization commands")
benchmark_app = typer.Typer(help="Benchmark commands")

app.add_typer(config_app, name="config")
app.add_typer(providers_app, name="providers")
app.add_typer(models_app, name="models")
app.add_typer(analytics_app, name="analytics")
app.add_typer(requests_app, name="requests")
app.add_typer(org_app, name="org")
app.add_typer(benchmark_app, name="benchmark")
governance_app = typer.Typer(help="AI governance commands")
policies_gov_app = typer.Typer(help="Governance policies")
approvals_gov_app = typer.Typer(help="Approval requests")
events_gov_app = typer.Typer(help="Governance events")
app.add_typer(governance_app, name="governance")
governance_app.add_typer(policies_gov_app, name="policies")
governance_app.add_typer(approvals_gov_app, name="approvals")
governance_app.add_typer(events_gov_app, name="events")
agents_app = typer.Typer(help="Agent commands")
executions_app = typer.Typer(help="Agent execution commands")
workflows_app = typer.Typer(help="Workflow commands")
app.add_typer(agents_app, name="agents")
agents_app.add_typer(executions_app, name="executions")
app.add_typer(workflows_app, name="workflows")
extensions_app = typer.Typer(help="Extension commands")
templates_app = typer.Typer(help="Template gallery commands")
app.add_typer(extensions_app, name="extensions")
app.add_typer(templates_app, name="templates")

console = Console()


def _print_json(data: object, as_json: bool) -> None:
    if as_json:
        console.print_json(json.dumps(data, default=str))
    else:
        console.print(data)


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-V", help="Show version"),
):
    if version:
        console.print(f"modelbridge {__version__}")
        raise typer.Exit()


# --- config ---

@config_app.command("set")
def config_set(key: str, value: str):
    """Set a configuration value (url, api-key, org-id)."""
    mapping = {"api-key": "api_key", "api_key": "api_key", "url": "url", "org-id": "org_id", "org_id": "org_id"}
    k = mapping.get(key, key)
    set_value(k, value)
    console.print(f"Set {k}")


@config_app.command("get")
def config_get(key: str):
    cfg = show_config()
    mapping = {"api-key": "api_key", "api_key": "api_key", "url": "url", "org-id": "org_id"}
    k = mapping.get(key, key)
    console.print(cfg.get(k, get(k)))


@config_app.command("show")
def config_show():
    for k, v in show_config().items():
        console.print(f"{k}: {v}")


@config_app.command("clear")
def config_clear():
    clear_config()
    console.print("Configuration cleared.")


@config_app.command("validate")
def config_validate():
    """Validate CLI configuration (does not reveal secrets)."""
    cfg = load_config()
    issues = []
    if not cfg.get("url"):
        issues.append("url is not set")
    if not cfg.get("api_key") and not cfg.get("access_token"):
        issues.append("Neither api_key nor access_token is set")
    try:
        client = CLIClient()
        health = client.get("/health", auth=False)
        console.print(f"Server: {health.get('status', 'unknown')} (v{health.get('version', '?')})")
    except Exception as e:
        issues.append(f"Cannot reach server: {e}")
    if issues:
        for i in issues:
            console.print(f"[red]✗[/red] {i}")
        raise typer.Exit(1)
    console.print("[green]✓[/green] Configuration looks valid")


# --- login ---

@app.command("login")
def login(
    email: str = typer.Option(..., prompt=True),
    password: str = typer.Option(..., prompt=True, hide_input=True),
):
    """Authenticate with email/password and store access token."""
    client = CLIClient()
    try:
        data = client.post("/auth/login", {"email": email, "password": password}, auth=False)
    except Exception as e:
        console.print(f"[red]Login failed:[/red] {e}")
        raise typer.Exit(1)
    save_config({
        "access_token": data["access_token"],
        "email": email,
        "org_id": data.get("user", {}).get("organization_id"),
    })
    console.print("[green]Logged in successfully.[/green]")


# --- status ---

@app.command("status")
def status(json_out: bool = typer.Option(False, "--json")):
    """Show server and dependency status."""
    client = CLIClient()
    try:
        health = client.get("/health", auth=False)
    except Exception as e:
        console.print(f"[red]Server unreachable:[/red] {e}")
        raise typer.Exit(1)

    info = {
        "server_status": health.get("status"),
        "version": health.get("version"),
        "checks": health.get("checks", {}),
        "url": client.base_url,
        "org_id": client.org_id,
    }
    if client.token:
        try:
            orgs = client.get("/organizations/", dashboard=True)
            info["organizations"] = len(orgs)
        except Exception:
            info["organizations"] = "auth required"
    if json_out:
        _print_json(info, True)
        return
    console.print(f"Server: {info['server_status']} (v{info['version']})")
    for k, v in info.get("checks", {}).items():
        console.print(f"  {k}: {v}")
    console.print(f"URL: {info['url']}")
    if info.get("org_id"):
        console.print(f"Active org: {info['org_id']}")


# --- providers ---

@providers_app.command("list")
def providers_list(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    try:
        providers = client.get("/providers/", dashboard=True)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}\nRun [bold]modelbridge login[/bold] for dashboard access.")
        raise typer.Exit(1)
    if json_out:
        _print_json(providers, True)
        return
    table = Table(title="Providers")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Enabled")
    for p in providers:
        table.add_row(p.get("name", ""), p.get("type", ""), p.get("status", ""), str(p.get("is_enabled", "")))
    console.print(table)


# --- models ---

@models_app.command("list")
def models_list(
    provider: Optional[str] = typer.Option(None, "--provider"),
    capability: Optional[str] = typer.Option(None, "--capability"),
    available: bool = typer.Option(False, "--available"),
    json_out: bool = typer.Option(False, "--json"),
):
    client = CLIClient()
    try:
        models = client.get("/models/", dashboard=True)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if capability:
        cap_map = {
            "chat": "supports_chat",
            "streaming": "supports_streaming",
            "tools": "supports_tools",
            "vision": "supports_vision",
            "embeddings": "supports_embeddings",
            "json": "supports_json_mode",
        }
        field = cap_map.get(capability.lower(), capability)
        models = [m for m in models if m.get(field)]

    if available:
        models = [m for m in models if m.get("is_enabled")]

    if json_out:
        _print_json(models, True)
        return

    table = Table(title="Models")
    table.add_column("Name")
    table.add_column("Provider ID")
    table.add_column("Enabled")
    for m in models:
        table.add_row(m.get("display_name", ""), m.get("provider_model_id", ""), str(m.get("is_enabled")))
    console.print(table)


# --- chat ---

@app.command("chat")
def chat_cmd(
    message: str = typer.Argument(..., help="User message"),
    model: str = typer.Option("auto", "--model", "-m"),
    temperature: Optional[float] = typer.Option(None, "--temperature", "-t"),
    max_tokens: Optional[int] = typer.Option(None, "--max-tokens"),
    stream: bool = typer.Option(False, "--stream"),
):
    """Send a chat completion through the gateway."""
    client = CLIClient()
    body: dict = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "stream": stream,
    }
    if temperature is not None:
        body["temperature"] = temperature
    if max_tokens is not None:
        body["max_tokens"] = max_tokens

    try:
        if stream:
            import json as _json

            for chunk in client.stream_post("/v1/chat/completions", body):
                if chunk == "[DONE]":
                    break
                data = _json.loads(chunk)
                delta = data.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content")
                if content:
                    console.print(content, end="")
            console.print()
        else:
            result = client.post("/v1/chat/completions", body, gateway=True)
            content = result["choices"][0]["message"].get("content", "")
            console.print(content)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# --- embeddings ---

@app.command("embeddings")
def embeddings_cmd(
    text: str = typer.Argument(..., help="Text to embed"),
    model: str = typer.Option("auto", "--model", "-m"),
    json_out: bool = typer.Option(False, "--json"),
):
    client = CLIClient()
    try:
        result = client.post("/v1/embeddings", {"model": model, "input": text}, gateway=True)
        if json_out:
            _print_json(result, True)
        else:
            dims = len(result["data"][0]["embedding"])
            console.print(f"Embedding dimensions: {dims}")
            console.print(f"Model: {result.get('model')}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# --- analytics ---

@analytics_app.command("overview")
def analytics_overview(
    days: int = typer.Option(30, "--days"),
    json_out: bool = typer.Option(False, "--json"),
):
    client = CLIClient()
    start = (datetime.utcnow() - timedelta(days=days)).isoformat()
    try:
        data = client.get("/analytics/overview", dashboard=True, params={"start_date": start})
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    _print_json(data, json_out)


@analytics_app.command("providers")
def analytics_providers(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/analytics/providers", dashboard=True)
    _print_json(data, json_out)


# --- requests ---

@requests_app.command("list")
def requests_list(
    status: Optional[str] = typer.Option(None, "--status"),
    limit: int = typer.Option(20, "--limit"),
    json_out: bool = typer.Option(False, "--json"),
):
    client = CLIClient()
    params: dict = {"limit": limit}
    if status:
        params["status"] = status
    data = client.get("/logs/", dashboard=True, params=params)
    _print_json(data, json_out)


@requests_app.command("get")
def requests_get(request_id: str, json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get(f"/logs/{request_id}", dashboard=True)
    _print_json(data, json_out)


# --- org ---

@org_app.command("list")
def org_list(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/organizations/", dashboard=True)
    _print_json(data, json_out)


@org_app.command("current")
def org_current(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/organizations/current", dashboard=True)
    _print_json(data, json_out)


@org_app.command("switch")
def org_switch(organization_id: str):
    client = CLIClient()
    data = client.post(f"/organizations/current/switch?organization_id={organization_id}", {}, dashboard=True)
    save_config({
        "access_token": data["access_token"],
        "org_id": data.get("user", {}).get("organization_id"),
    })
    console.print("[green]Organization switched.[/green]")


# --- benchmark ---

@benchmark_app.command("run")
def benchmark_run(
    model: str = typer.Option("auto", "--model"),
    count: int = typer.Option(5, "--count"),
    prompt: str = typer.Option("Hello", "--prompt"),
):
    """Run a simple latency benchmark (environment-dependent results)."""
    import statistics
    import time

    client = CLIClient()
    latencies: list[float] = []
    errors = 0
    for i in range(count):
        start = time.time()
        try:
            client.post(
                "/v1/chat/completions",
                {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False, "max_tokens": 32},
                gateway=True,
            )
            latencies.append((time.time() - start) * 1000)
        except Exception:
            errors += 1

    if not latencies:
        console.print("[red]All requests failed[/red]")
        raise typer.Exit(1)

    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0]
    console.print(f"Model: {model}")
    console.print(f"Requests: {count} | Success: {len(latencies)} | Errors: {errors}")
    console.print(f"Avg latency: {statistics.mean(latencies):.0f} ms")
    console.print(f"P50: {p50:.0f} ms | P95: {p95:.0f} ms")
    console.print("[dim]Results are environment-dependent — not universal rankings.[/dim]")


@policies_gov_app.command("list")
def governance_policies_list(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/governance/policies", dashboard=True)
    _print_json(data, json_out)


@policies_gov_app.command("get")
def governance_policies_get(policy_id: str, json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get(f"/governance/policies/{policy_id}", dashboard=True)
    _print_json(data, json_out)


@events_gov_app.command("list")
def governance_events_list(
    json_out: bool = typer.Option(False, "--json"),
    days: int = typer.Option(30, "--days"),
):
    client = CLIClient()
    data = client.get("/governance/events", dashboard=True, params={"days": days})
    _print_json(data, json_out)


@approvals_gov_app.command("list")
def governance_approvals_list(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/governance/approvals", dashboard=True)
    _print_json(data, json_out)


@agents_app.command("list")
def agents_list(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/agents", dashboard=True)
    _print_json(data, json_out)


@agents_app.command("get")
def agents_get(agent_id: str, json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get(f"/agents/{agent_id}", dashboard=True)
    _print_json(data, json_out)


@agents_app.command("execute")
def agents_execute(
    agent_id: str,
    input_text: str = typer.Option("", "--input"),
    sync: bool = typer.Option(False, "--sync"),
    json_out: bool = typer.Option(False, "--json"),
):
    client = CLIClient()
    data = client.post(
        f"/agents/{agent_id}/execute",
        {"input_text": input_text or None, "sync": sync},
        dashboard=True,
    )
    _print_json(data, json_out)


@executions_app.command("list")
def agent_executions_list(
    agent_id: Optional[str] = typer.Option(None, "--agent-id"),
    json_out: bool = typer.Option(False, "--json"),
):
    client = CLIClient()
    path = "/agents/executions/list"
    if agent_id:
        path += f"?agent_id={agent_id}"
    data = client.get(path, dashboard=True)
    _print_json(data, json_out)


@workflows_app.command("list")
def workflows_list(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/workflows", dashboard=True)
    _print_json(data, json_out)


@workflows_app.command("execute")
def workflows_execute(
    workflow_id: str,
    sync: bool = typer.Option(False, "--sync"),
    json_out: bool = typer.Option(False, "--json"),
):
    client = CLIClient()
    data = client.post(
        f"/workflows/{workflow_id}/execute",
        {"sync": sync},
        dashboard=True,
    )
    _print_json(data, json_out)


@extensions_app.command("list")
def extensions_list(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/extensions/installations", dashboard=True)
    _print_json(data, json_out)


@extensions_app.command("packages")
def extensions_packages(
    json_out: bool = typer.Option(False, "--json"),
    plugin_type: Optional[str] = typer.Option(None, "--type"),
):
    client = CLIClient()
    params = {"plugin_type": plugin_type} if plugin_type else None
    data = client.get("/extensions/packages", dashboard=True, params=params)
    _print_json(data, json_out)


@extensions_app.command("install")
def extensions_install(
    package_version_id: str,
    permissions: str = typer.Option("", "--permissions", help="Comma-separated approved permissions"),
    enable: bool = typer.Option(False, "--enable"),
    json_out: bool = typer.Option(False, "--json"),
):
    client = CLIClient()
    perms = [p.strip() for p in permissions.split(",") if p.strip()]
    data = client.post(
        "/extensions/installations",
        {
            "package_version_id": package_version_id,
            "approved_permissions": perms,
            "enable": enable,
        },
        dashboard=True,
    )
    _print_json(data, json_out)


@extensions_app.command("enable")
def extensions_enable(installation_id: str, json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.post(f"/extensions/installations/{installation_id}/enable", {}, dashboard=True)
    _print_json(data, json_out)


@extensions_app.command("disable")
def extensions_disable(installation_id: str, json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.post(f"/extensions/installations/{installation_id}/disable", {}, dashboard=True)
    _print_json(data, json_out)


@templates_app.command("list")
def templates_list(
    json_out: bool = typer.Option(False, "--json"),
    plugin_type: Optional[str] = typer.Option(None, "--type"),
):
    client = CLIClient()
    params = {"plugin_type": plugin_type} if plugin_type else None
    data = client.get("/templates", dashboard=True, params=params)
    _print_json(data, json_out)


workspaces_app = typer.Typer(help="Workspace commands")
projects_app = typer.Typer(help="Project commands")
fleet_app = typer.Typer(help="Fleet commands")
app.add_typer(workspaces_app, name="workspaces")
app.add_typer(projects_app, name="projects")
app.add_typer(fleet_app, name="fleet")


@workspaces_app.command("list")
def workspaces_list(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/workspaces", dashboard=True)
    _print_json(data, json_out)


@projects_app.command("list")
def projects_list(
    workspace_id: Optional[str] = typer.Option(None, "--workspace-id"),
    json_out: bool = typer.Option(False, "--json"),
):
    client = CLIClient()
    params = {"workspace_id": workspace_id} if workspace_id else None
    data = client.get("/projects", dashboard=True, params=params)
    _print_json(data, json_out)


@fleet_app.command("list")
def fleet_list(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/fleet", dashboard=True)
    _print_json(data, json_out)


@fleet_app.command("status")
def fleet_status(instance_id: str, json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get(f"/fleet/{instance_id}", dashboard=True)
    _print_json(data, json_out)


cloud_app = typer.Typer(help="Cloud platform commands")
cloud_regions_app = typer.Typer(help="Region commands")
cloud_instances_app = typer.Typer(help="Managed instance commands")
usage_app = typer.Typer(help="Usage metering commands")
app.add_typer(cloud_app, name="cloud")
cloud_app.add_typer(cloud_regions_app, name="regions")
cloud_app.add_typer(cloud_instances_app, name="instances")
app.add_typer(usage_app, name="usage")


@cloud_app.command("health")
def cloud_health(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/cloud/health", dashboard=True)
    _print_json(data, json_out)


@cloud_regions_app.command("list")
def cloud_regions_list(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/cloud/regions", dashboard=True)
    _print_json(data, json_out)


@cloud_instances_app.command("list")
def cloud_instances_list(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/cloud/instances", dashboard=True)
    _print_json(data, json_out)


@usage_app.command("summary")
def usage_summary(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/usage/summary", dashboard=True)
    _print_json(data, json_out)


intelligence_app = typer.Typer(help="Operational intelligence commands")
app.add_typer(intelligence_app, name="intelligence")


@intelligence_app.command("overview")
def intelligence_overview(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/intelligence/overview", dashboard=True)
    _print_json(data, json_out)


@intelligence_app.command("providers")
def intelligence_providers(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/intelligence/providers", dashboard=True)
    _print_json(data, json_out)


@intelligence_app.command("costs")
def intelligence_costs(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/intelligence/costs", dashboard=True)
    _print_json(data, json_out)


@intelligence_app.command("anomalies")
def intelligence_anomalies(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/intelligence/anomalies", dashboard=True)
    _print_json(data, json_out)


@intelligence_app.command("recommendations")
def intelligence_recommendations(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/intelligence/recommendations", dashboard=True)
    _print_json(data, json_out)


events_app = typer.Typer(help="Platform event commands")
webhooks_app = typer.Typer(help="Webhook commands")
integrations_app = typer.Typer(help="Integration commands")
automations_app = typer.Typer(help="Automation commands")
app.add_typer(events_app, name="events")
app.add_typer(webhooks_app, name="webhooks")
app.add_typer(integrations_app, name="integrations")
app.add_typer(automations_app, name="automations")


@events_app.command("list")
def events_list(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/events", dashboard=True)
    _print_json(data, json_out)


@events_app.command("catalog")
def events_catalog(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/events/catalog", dashboard=True)
    _print_json(data, json_out)


@webhooks_app.command("list")
def webhooks_list(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/webhooks", dashboard=True)
    _print_json(data, json_out)


@webhooks_app.command("create")
def webhooks_create(
    name: str = typer.Option(..., "--name"),
    url: str = typer.Option(..., "--url"),
    events: str = typer.Option(..., "--events", help="Comma-separated event types"),
    json_out: bool = typer.Option(False, "--json"),
):
    client = CLIClient()
    data = client.post(
        "/webhooks",
        {"name": name, "url": url, "event_types": [e.strip() for e in events.split(",") if e.strip()]},
        dashboard=True,
    )
    _print_json(data, json_out)


@integrations_app.command("list")
def integrations_list(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/integrations", dashboard=True)
    _print_json(data, json_out)


@automations_app.command("list")
def automations_list(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/automations", dashboard=True)
    _print_json(data, json_out)


marketplace_app = typer.Typer(help="Marketplace commands")
app.add_typer(marketplace_app, name="marketplace")

studio_app = typer.Typer(help="AI Studio commands")
studio_workflows_app = typer.Typer(help="Studio workflow commands")
prompts_app = typer.Typer(help="Prompt template commands")
evaluations_app = typer.Typer(help="Evaluation commands")
app.add_typer(studio_app, name="studio")
studio_app.add_typer(studio_workflows_app, name="workflows")
app.add_typer(prompts_app, name="prompts")
app.add_typer(evaluations_app, name="evaluations")


quality_app = typer.Typer(help="AI Quality Platform commands")
app.add_typer(quality_app, name="quality")

finops_app = typer.Typer(help="AI FinOps commands")
app.add_typer(finops_app, name="finops")


@finops_app.command("overview")
def finops_overview(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/finops/overview", dashboard=True)
    _print_json(data, json_out)


@finops_app.command("costs")
def finops_costs(
    days: int = typer.Option(30, "--days"),
    json_out: bool = typer.Option(False, "--json"),
):
    client = CLIClient()
    data = client.get("/finops/costs", dashboard=True, params={"days": str(days)})
    _print_json(data, json_out)


@finops_app.command("budgets")
def finops_budgets_list(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/finops/budgets", dashboard=True)
    _print_json(data, json_out)


@finops_app.command("forecast")
def finops_forecast(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/finops/forecast", dashboard=True)
    _print_json(data, json_out)


@finops_app.command("optimize")
def finops_optimize(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/finops/recommendations", dashboard=True)
    _print_json(data, json_out)


@studio_app.command("overview")
def studio_overview(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/studio/overview", dashboard=True)
    _print_json(data, json_out)


@studio_workflows_app.command("list")
def studio_workflows_list(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/studio/workflows", dashboard=True)
    _print_json(data, json_out)


@prompts_app.command("list")
def prompts_list(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/prompts/", dashboard=True)
    _print_json(data, json_out)


@prompts_app.command("test")
def prompts_test(
    prompt_id: str,
    input_text: str = typer.Option("Hello", "--input", "-i"),
    json_out: bool = typer.Option(False, "--json"),
):
    client = CLIClient()
    data = client.post(f"/prompts/{prompt_id}/test", {"input": input_text, "model": "auto"}, dashboard=True)
    _print_json(data, json_out)


@evaluations_app.command("run")
def evaluations_run(suite_id: str, json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.post(f"/evaluations/{suite_id}/run", {}, dashboard=True)
    _print_json(data, json_out)


@evaluations_app.command("datasets")
def evaluations_datasets(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/evaluations/datasets", dashboard=True)
    _print_json(data, json_out)


@quality_app.command("overview")
def quality_overview(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/quality/overview", dashboard=True)
    _print_json(data, json_out)


@quality_app.command("pipelines")
def quality_pipelines_list(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/quality/pipelines", dashboard=True)
    _print_json(data, json_out)


@quality_app.command("run")
def quality_run(pipeline_id: str, json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.post(f"/quality/pipelines/{pipeline_id}/run", {}, dashboard=True)
    _print_json(data, json_out)


@quality_app.command("regressions")
def quality_regressions(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/quality/regressions", dashboard=True)
    _print_json(data, json_out)


@marketplace_app.command("search")
def marketplace_search(
    query: str = typer.Option(None, "--query", "-q"),
    content_type: str = typer.Option(None, "--type"),
    json_out: bool = typer.Option(False, "--json"),
):
    client = CLIClient()
    params = {}
    if query:
        params["q"] = query
    if content_type:
        params["content_type"] = content_type
    data = client.get("/marketplace/items", dashboard=True, params=params or None)
    _print_json(data, json_out)


@marketplace_app.command("list")
def marketplace_list(json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get("/marketplace/items", dashboard=True)
    _print_json(data, json_out)


@marketplace_app.command("info")
def marketplace_info(slug: str, json_out: bool = typer.Option(False, "--json")):
    client = CLIClient()
    data = client.get(f"/marketplace/items/{slug}", dashboard=True)
    _print_json(data, json_out)


@marketplace_app.command("install")
def marketplace_install(
    slug: str,
    permissions: str = typer.Option("", "--permissions", help="Comma-separated permissions to approve"),
    json_out: bool = typer.Option(False, "--json"),
):
    client = CLIClient()
    info = client.get(f"/marketplace/items/{slug}", dashboard=True)
    item_id = info["id"]
    perms = [p.strip() for p in permissions.split(",") if p.strip()] if permissions else []
    if not perms and info.get("current_version"):
        perms = info["current_version"].get("permissions", [])
    data = client.post(
        f"/marketplace/items/{item_id}/install",
        {"approved_permissions": perms, "enable": True},
        dashboard=True,
    )
    _print_json(data, json_out)


if __name__ == "__main__":
    app()
