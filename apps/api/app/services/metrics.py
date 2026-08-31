"""Prometheus metrics for ModelBridge.

Exposed at GET /metrics. Labels are bounded — no request_id or user_id.
"""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUESTS_TOTAL = Counter(
    "modelbridge_requests_total",
    "Total AI gateway requests",
    ["status", "provider"],
)

REQUEST_DURATION = Histogram(
    "modelbridge_request_duration_seconds",
    "Request duration in seconds",
    ["provider"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

PROVIDER_REQUESTS = Counter(
    "modelbridge_provider_requests_total",
    "Requests per provider",
    ["provider", "status"],
)

PROVIDER_ERRORS = Counter(
    "modelbridge_provider_errors_total",
    "Provider errors by type",
    ["provider", "error_type"],
)

TOKENS_TOTAL = Counter(
    "modelbridge_tokens_total",
    "Total tokens processed",
    ["direction", "provider"],
)

CACHE_EVENTS = Counter(
    "modelbridge_cache_events_total",
    "Response cache events",
    ["event", "endpoint"],
)

POLICY_EVALUATIONS = Counter(
    "modelbridge_policy_evaluations_total",
    "Governance policy evaluations",
    ["decision"],
)

POLICY_BLOCKS = Counter(
    "modelbridge_policy_blocks_total",
    "Requests blocked by governance",
    ["reason_code"],
)

SENSITIVE_DATA_EVENTS = Counter(
    "modelbridge_sensitive_data_events_total",
    "Sensitive data detections by category label",
    ["category"],
)

REDACTIONS_TOTAL = Counter(
    "modelbridge_redactions_total",
    "Redactions applied",
    ["stage"],
)

APPROVAL_REQUESTS = Counter(
    "modelbridge_approval_requests_total",
    "Approval workflow events",
    ["status"],
)

GOVERNANCE_EVENTS = Counter(
    "modelbridge_governance_events_total",
    "Governance events by type",
    ["event_type"],
)

AGENT_EXECUTIONS = Counter(
    "modelbridge_agent_executions_total",
    "Agent execution outcomes",
    ["status"],
)

AGENT_STEPS = Counter(
    "modelbridge_agent_steps_total",
    "Agent execution steps",
    ["step_type", "status"],
)

AGENT_TOOL_CALLS = Counter(
    "modelbridge_agent_tool_calls_total",
    "Agent tool invocations",
    ["tool_name", "status"],
)

AGENT_EXECUTION_DURATION = Histogram(
    "modelbridge_agent_execution_duration_seconds",
    "Agent execution duration",
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 120, 300, 600),
)

WORKFLOW_EXECUTIONS = Counter(
    "modelbridge_workflow_executions_total",
    "Workflow execution outcomes",
    ["status"],
)

EXTENSION_EVENTS = Counter(
    "modelbridge_extension_executions_total",
    "Extension lifecycle and execution events",
    ["event", "plugin_type"],
)

EXTENSION_FAILURES = Counter(
    "modelbridge_extension_failures_total",
    "Extension failures",
    ["plugin_type"],
)

INSTANCES_TOTAL = Counter(
    "modelbridge_instances_total",
    "Managed instance events",
    ["event"],
)

INSTANCE_HEARTBEATS = Counter(
    "modelbridge_instance_heartbeats_total",
    "Instance heartbeats",
    ["status"],
)

CONFIG_DEPLOYMENTS = Counter(
    "modelbridge_configuration_deployments_total",
    "Configuration deployments",
    ["status"],
)

CONFIG_DEPLOYMENT_FAILURES = Counter(
    "modelbridge_configuration_deployment_failures_total",
    "Failed configuration deployments",
)

REGIONS_TOTAL = Counter(
    "modelbridge_regions_total",
    "Region lifecycle events",
    ["event"],
)

REGION_HEALTH = Counter(
    "modelbridge_region_health_status",
    "Region status changes",
    ["region", "status"],
)

FAILOVER_EVENTS = Counter(
    "modelbridge_failover_events_total",
    "Failover events",
    ["verified"],
)

MANAGED_INSTANCES = Counter(
    "modelbridge_managed_instances_total",
    "Managed instance lifecycle events",
    ["status"],
)

CONFIG_ROLLOUTS = Counter(
    "modelbridge_configuration_rollouts_total",
    "Configuration rollouts by status",
    ["status"],
)


def record_cache_event(event: str, endpoint: str) -> None:
    """Record cache hit/miss/write/bypass/error."""
    CACHE_EVENTS.labels(event=event, endpoint=endpoint).inc()


def record_governance_event(event_type: str, decision: str) -> None:
    bounded_type = event_type if len(event_type) < 80 else "other"
    GOVERNANCE_EVENTS.labels(event_type=bounded_type).inc()
    POLICY_EVALUATIONS.labels(decision=decision[:40]).inc()
    if bounded_type == "policy.blocked":
        POLICY_BLOCKS.labels(reason_code="policy").inc()
    if bounded_type == "sensitive_data.detected":
        SENSITIVE_DATA_EVENTS.labels(category="detected").inc()
    if bounded_type in {"redaction.applied", "response.redacted"}:
        stage = "response" if bounded_type.startswith("response") else "prompt"
        REDACTIONS_TOTAL.labels(stage=stage).inc()
    if bounded_type == "approval.requested":
        APPROVAL_REQUESTS.labels(status="pending").inc()


def record_agent_execution(status: str) -> None:
    AGENT_EXECUTIONS.labels(status=status[:30]).inc()


def record_agent_step(step_type: str, status: str) -> None:
    AGENT_STEPS.labels(step_type=step_type[:20], status=status[:20]).inc()


def record_agent_tool_call(tool_name: str, status: str) -> None:
    bounded = tool_name if len(tool_name) < 40 else "other"
    AGENT_TOOL_CALLS.labels(tool_name=bounded, status=status[:20]).inc()


def record_workflow_execution(status: str) -> None:
    WORKFLOW_EXECUTIONS.labels(status=status[:30]).inc()


def record_extension_event(event: str, plugin_type: str) -> None:
    EXTENSION_EVENTS.labels(event=event[:20], plugin_type=plugin_type[:20]).inc()


def record_instance_heartbeat(status: str) -> None:
    INSTANCE_HEARTBEATS.labels(status=status[:20]).inc()


def record_config_deployment(status: str, *, failed: bool = False) -> None:
    CONFIG_DEPLOYMENTS.labels(status=status[:20]).inc()
    if failed:
        CONFIG_DEPLOYMENT_FAILURES.inc()


def record_region_status(region: str, status: str) -> None:
    bounded = region if len(region) < 40 else "other"
    REGION_HEALTH.labels(region=bounded, status=status[:20]).inc()


def record_failover_event(*, verified: bool = False) -> None:
    FAILOVER_EVENTS.labels(verified="true" if verified else "false").inc()


def record_managed_instance_lifecycle(status: str) -> None:
    MANAGED_INSTANCES.labels(status=status[:20]).inc()


def record_configuration_rollout(status: str) -> None:
    CONFIG_ROLLOUTS.labels(status=status[:20]).inc()


def record_request(
    status: str,
    provider: str,
    duration_seconds: float,
    input_tokens: int = 0,
    output_tokens: int = 0,
    error_type: str | None = None,
) -> None:
    REQUESTS_TOTAL.labels(status=status, provider=provider).inc()
    REQUEST_DURATION.labels(provider=provider).observe(duration_seconds)
    PROVIDER_REQUESTS.labels(provider=provider, status=status).inc()
    if error_type:
        PROVIDER_ERRORS.labels(provider=provider, error_type=error_type).inc()
    if input_tokens:
        TOKENS_TOTAL.labels(direction="input", provider=provider).inc(input_tokens)
    if output_tokens:
        TOKENS_TOTAL.labels(direction="output", provider=provider).inc(output_tokens)


def metrics_response() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
