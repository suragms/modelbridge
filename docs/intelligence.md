# ModelBridge Intelligence Layer (Phase 13)

Evidence-based operational intelligence built from real telemetry — not fabricated predictions.

## Architecture

```text
Telemetry + Usage + Costs + Health
                │
                ▼
        Intelligence Engine
                │
     ┌──────────┼──────────┐
     ▼          ▼          ▼
 Forecasts   Anomalies  Recommendations
     │          │          │
     └──────────┼──────────┘
                ▼
       Human Review / Approval
                │
                ▼
         Controlled Action
```

Default automation level: **RECOMMEND** — high-impact changes require approval.

## Data Sources

| Source | Used For |
|--------|----------|
| `request_logs` | Latency, errors, success rate |
| `usage_records` / `cost_records` | Tokens, actual vs estimated cost |
| `usage_meter_events` | Agent/workflow metering |
| `providers` health columns | Provider availability |
| `configuration_deployments` | Incident correlation |
| `agent_executions` | Agent failure rates |

No raw prompt content is stored in intelligence tables.

## Data Quality

Every analysis returns:

- `sample_size`
- `time_range`
- `confidence`
- `status`: `sufficient` | `insufficient_data` | `partial`

When data is insufficient, APIs return `insufficient_data` instead of invented predictions.

## Features (Implemented)

- **Provider intelligence** — success rate, latency, explainable ranking
- **Cost intelligence** — actual vs estimated cost breakdown
- **Capacity analysis** — load trends and risk indicators
- **Forecasting** — linear trend for requests/cost with confidence
- **Anomaly detection** — z-score on daily latency/error series
- **Recommendations** — persistent, explainable, lifecycle-managed
- **Incident intelligence** — observed / correlated / hypothesis labels
- **Reliability scoring** — weighted, documented formula
- **Operations assistant** — rule-based NL queries (no raw SQL)
- **Background jobs** — daily analysis via ARQ cron (04:00 UTC)

## APIs

| Endpoint | Description |
|----------|-------------|
| `GET /intelligence/overview` | Dashboard summary |
| `GET /intelligence/providers` | Provider analysis |
| `GET /intelligence/costs` | FinOps breakdown |
| `GET /intelligence/capacity` | Capacity risks |
| `GET /intelligence/anomalies` | Detected anomalies |
| `POST /intelligence/anomalies/detect` | Run detection |
| `GET /intelligence/recommendations` | List recommendations |
| `POST /intelligence/recommendations/{id}/approve` | Approve (RBAC) |
| `POST /operations-assistant/query` | NL operations Q&A |

## RBAC

- `intelligence.read` — view intelligence and ask assistant
- `intelligence.manage` — run analysis, dismiss recommendations
- `intelligence.approve` — approve actionable recommendations

## Limitations

1. Forecasts use simple linear trends — not ML models
2. Anomaly detection requires ≥14 days of daily samples
3. Assistant uses keyword routing — not a general LLM over your database
4. Recommendations do not auto-modify routing or configuration
5. Cross-tenant access is blocked at the API layer

## Phase 14 Roadmap

- ML-based forecasting with seasonality
- LLM-powered assistant with tool-scoped retrieval
- Automated low-risk actions (cache tuning) with approval gates
- Project/environment scoped intelligence
