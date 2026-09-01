# AI FinOps & Cost Intelligence (Phase 18)

ModelBridge FinOps provides unified cost tracking, budgets, forecasting, anomaly detection, and optimization on top of existing observability cost records.

## Architecture

```
AI Request → Usage Collection → Cost Engine → Attribution / Budgets / Forecasts → Dashboards
```

Built on Phase 3 `CostRecord`/`UsageRecord`, Phase 5 budget enforcement, and Phase 13 cost intelligence.

## Cost Types

| Type | Meaning |
|------|---------|
| `actual` | Provider-reported or verified pricing |
| `estimated` | Calculated from configured pricing |
| `configured` | Manual pricing registry entry |
| `unknown` | No pricing available |

**Never display estimated costs as actual.**

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/finops/overview` | Dashboard summary |
| GET | `/finops/costs` | Cost explorer with breakdowns |
| GET/POST | `/finops/budgets` | Budget management |
| GET | `/finops/budgets/{id}/status` | Budget utilization |
| GET | `/finops/forecast` | Cost forecast with methodology |
| GET | `/finops/anomalies` | Cost anomalies with evidence |
| GET | `/finops/recommendations` | Optimization recommendations |
| GET | `/finops/models/comparison` | Model cost comparison |
| POST | `/finops/pricing` | Versioned provider pricing |
| GET | `/finops/reports/showback` | Showback reports |

## Budgets

Scoped budgets (organization, team, project) with thresholds at 50%, 75%, 90%, 100%. Enforcement actions: `alert`, `require_approval`, `restrict_requests`.

## Forecasting

Linear trend extrapolation from historical `CostRecord` data. Includes method, confidence, and limitations. Not a billing guarantee.

## Optimization

Recommendations include evidence, projected savings (labeled `projected`), assumptions, confidence, and risk. High-impact changes require approval — no automatic production changes.

## Events

- `budget.threshold.crossed`
- `budget.limit.reached`
- `cost.anomaly.detected`
- `forecast.overrun.predicted`
- `optimization.recommendation.created`

## CLI

```bash
modelbridge finops overview --json
modelbridge finops costs --days 30 --json
modelbridge finops budgets --json
modelbridge finops forecast --json
modelbridge finops optimize --json
```

## Metrics

- `modelbridge_cost_records_total`
- `modelbridge_budget_threshold_events_total`
- `modelbridge_cost_anomalies_total`
- `modelbridge_optimization_recommendations_total`

## Limitations

- Most costs are **estimated** from configured pricing, not provider invoices
- Projected savings are not realized until measured
- Chargeback/showback reports do not integrate with external accounting systems
- Team/project attribution requires `FinopsCostAttribution` records to be populated
- Forecasts do not account for pricing changes or seasonality

## Security

- Organization isolation on all FinOps resources
- RBAC: `finops.read`, `finops.manage`
- Cross-tenant access returns 404
- Governance audits track budget and policy changes
