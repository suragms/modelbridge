# Observability

ModelBridge Phase 3 provides production-grade observability built on **real request data**.

## Request Tracking

Every AI request receives a unique ID (`req_<hex>`). The full lifecycle is tracked:

`ROUTING → PROCESSING → COMPLETED | FAILED`

Request records store routing metadata, latency, token usage, and estimated cost. **Prompts and responses are never stored by default.**

## Usage Tracking

| Source | Meaning |
|--------|---------|
| `PROVIDER_REPORTED` | Actual usage from the provider response |
| `ESTIMATED` | Character-based heuristic (labeled as estimated) |
| `UNAVAILABLE` | No usage data available |

## Cost Estimation

Costs are calculated from the pricing registry:

```
input_cost = (input_tokens / 1_000_000) × input_price_per_million_tokens
```

> **Cost values are estimates and may not exactly match provider invoices.**

Local providers (Ollama, LM Studio) default to **Unknown / Not Configured** unless administrators set custom pricing.

## Analytics APIs

| Endpoint | Description |
|----------|-------------|
| `GET /analytics/overview` | Summary metrics |
| `GET /analytics/requests` | Requests time series |
| `GET /analytics/tokens` | Token usage time series |
| `GET /analytics/cost` | Estimated cost time series |
| `GET /analytics/latency` | Latency time series |
| `GET /analytics/providers` | Provider breakdown + performance |
| `GET /analytics/models` | Model breakdown |
| `GET /analytics/errors` | Error list + time series |
| `GET /analytics/api-keys` | Per-key usage |

All endpoints support `start_date` and `end_date` filters.

## Request Logs

| Endpoint | Description |
|----------|-------------|
| `GET /logs` | Paginated, filterable request list |
| `GET /logs/{request_id}` | Full request detail |

## Prometheus

Scrape `GET /metrics` for:

- `modelbridge_requests_total`
- `modelbridge_request_duration_seconds`
- `modelbridge_provider_requests_total`
- `modelbridge_provider_errors_total`
- `modelbridge_tokens_total`

Labels are bounded (no `request_id` or `user_id`).

## Audit Logs

`GET /audit` returns administrator actions (login, provider changes, API key events, routing policy changes). Secrets are never stored.

## OpenTelemetry

An abstraction layer (`app/observability/tracing.py`) is ready for OTLP export. Full distributed tracing is not enabled by default.

## Data Retention

Configure retention in environment variables:

```bash
REQUEST_LOG_RETENTION_DAYS=30
ANALYTICS_RETENTION_DAYS=90
AUDIT_LOG_RETENTION_DAYS=180
```

Automatic cleanup requires a background scheduler (not included in this phase).

## Privacy

- API keys, provider secrets, and passwords are never logged
- Audit metadata is sanitized
- Error responses do not expose stack traces
