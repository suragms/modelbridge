# AI Governance

ModelBridge includes an organization-scoped governance layer that evaluates requests **before** provider execution.

Governance controls depend on configured policies and heuristic detection. They should **not** be interpreted as a guarantee of legal or regulatory compliance.

## Pipeline

```text
Auth → Org → RBAC/scopes → Rate limit/quota
  → Policy evaluation → Sensitive data detection → Risk classification
  → Model authorization → Routing (authorized candidates only)
  → Provider execution → Response policy → Audit → Response
```

## Policy engine

Policies are stored per organization with:

- `priority` (lower number evaluated first)
- structured JSON `rules` (no code execution)
- actions: `allow`, `warn`, `deny`, `require_approval`, `redact`

**Conflict rule:** `DENY` overrides `ALLOW`. Organization DENY cannot be bypassed by an API-key ALLOW.

Severity order: `DENY > REQUIRE_APPROVAL > REDACT > WARN > ALLOW`

### Rule example

```json
{
  "conditions": [
    { "field": "risk_level", "operator": "equals", "value": "HIGH" }
  ],
  "match": "all",
  "allowed_models": ["llama3"],
  "blocked_models": ["blocked-model"],
  "local_only": true
}
```

Allowed condition fields: `risk_level`, `classification`, `requested_model`, `provider_type`, `capability`, `has_pii`, `has_secret`, `api_key_id`, `deployment_type`, `request_type`, `endpoint`.

## Model and provider restrictions

Allowlists and blocklists are applied **before** routing optimization. Blocked models never receive fallback or experiment traffic. Auto-routing only considers authorized candidates.

Provider `deployment_type`, `region`, and `data_residency` are configuration metadata. ModelBridge does not infer legal residency automatically.

Local providers are those configured as `ollama` or `lmstudio` — remote APIs are never labeled local.

## Sensitive data

Baseline detectors (pattern-based):

- Email, phone, government-ID-like numbers, payment-card-like numbers
- PEM keys, AWS keys, GitHub/Slack tokens, JWT-like strings, password assignments

**Limitations:** false positives and false negatives are expected. This is not a DLP product.

Detected **values are never stored** in governance logs — only category labels.

### Redaction

When enabled (`redact_prompts` / policy action `redact`):

- Replacement tokens such as `[EMAIL_REDACTED]` are applied to the **in-memory copy sent to the provider**
- Original request-log storage is not rewritten by this step

## Request classification

Heuristic classes: `GENERAL`, `CODE`, `FINANCIAL`, `PERSONAL_DATA`, `SENSITIVE`, `HIGH_RISK`.

Risk levels: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`, with recorded reasons.

## Content safety

A local keyword heuristic is included. It is **not** comprehensive moderation. Plug in another backend via `ContentSafetyBackend` if needed.

## Approvals

When a policy action is `require_approval` and approvals are enabled:

1. An approval row is created (`pending` / `approved` / `rejected` / `expired`)
2. The gateway returns `403` with `APPROVAL_REQUIRED` and `approval_id`
3. After an authorized reviewer approves, **replay** the same request with header `X-ModelBridge-Approval-ID`

The original prompt is **not** auto-executed later. Safe snapshot metadata (risk, classification, redacted preview) is stored — not raw secrets.

## Caching

Cache keys include a **policy fingerprint**. Changing or versioning policies invalidates cached responses so stale answers cannot bypass new restrictions.

## APIs

All routes require JWT membership in the organization (`X-Organization-ID` supported):

| Method | Path |
|--------|------|
| GET/POST | `/governance/policies` |
| GET/PATCH/DELETE | `/governance/policies/{id}` |
| GET | `/governance/policies/{id}/versions` |
| POST | `/governance/simulate` |
| GET | `/governance/events` |
| GET | `/governance/overview` |
| GET | `/governance/reports` and `/governance/reports/export?fmt=csv\|json` |
| GET/POST | `/governance/approvals` … `/approve` `/reject` |
| GET/PATCH | `/governance/settings` |
| GET | `/governance/notifications` |

RBAC: `governance.read`, `governance.manage`, `governance.approve`.

## Dashboard

- `/governance` — overview from stored events
- `/governance/policies` and `/governance/policies/:id`
- `/governance/approvals`
- `/settings/governance/data-protection`

## CLI

```bash
modelbridge governance policies list --json
modelbridge governance policies get <id>
modelbridge governance events list --days 30
modelbridge governance approvals list
```
