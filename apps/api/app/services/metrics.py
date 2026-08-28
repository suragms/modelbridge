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


def record_cache_event(event: str, endpoint: str) -> None:
    """Record cache hit/miss/write/bypass/error."""
    CACHE_EVENTS.labels(event=event, endpoint=endpoint).inc()


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
