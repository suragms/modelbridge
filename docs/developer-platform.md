# Developer Platform (Phase 14)

ModelBridge Phase 14 adds an event-driven developer platform with webhooks, integrations, automations, and scoped API keys.

## Event Architecture

```
ModelBridge Action → Event Created → Event Bus → Subscribers
                                              ├─ Webhook
                                              ├─ Automation
                                              └─ Integration
```

Events are persisted in `platform_events` with organization isolation. Payloads are sanitized — secrets are never included.

## Event Catalog

| Type | Category |
|------|----------|
| `request.completed` | gateway |
| `request.failed` | gateway |
| `provider.degraded` | provider |
| `provider.recovered` | provider |
| `agent.started/completed/failed` | agent |
| `workflow.started/completed/failed` | workflow |
| `deployment.started/completed/failed` | deployment |
| `anomaly.detected` | intelligence |
| `recommendation.created` | intelligence |
| `integration.connected` | integration |
| `automation.triggered` | automation |

Full catalog: `GET /events/catalog`

## Event Envelope

```json
{
  "id": "uuid",
  "type": "request.completed",
  "organization_id": "uuid",
  "timestamp": "2026-08-31T12:00:00Z",
  "schema_version": "1.0",
  "data": { "request_id": "...", "provider": "openai" }
}
```

## Webhooks

### Management API

- `GET/POST /webhooks`
- `GET/PATCH/DELETE /webhooks/{id}`
- `POST /webhooks/{id}/rotate-secret`
- `GET /webhooks/{id}/deliveries`
- `POST /webhooks/{id}/deliveries/{delivery_id}/retry`

### Signing

Outbound webhooks include:

- `X-ModelBridge-Signature`: `t=<unix_ts>,v1=<hmac_sha256_hex>`
- `X-ModelBridge-Event-Id`
- `X-ModelBridge-Event-Type`

Verification uses HMAC-SHA256 over `{timestamp}.{body}`. Timestamps older than 300 seconds are rejected.

### Security

- HTTPS required in production
- SSRF protection blocks private IPs, localhost, `.internal`, `.local`
- Secrets encrypted at rest (Fernet)
- Secrets shown only once at creation/rotation

### Delivery States

`pending` → `delivering` → `delivered` | `retrying` → `failed`

Retries: exponential backoff (1m, 5m, 15m, 1h, 2h), max 5 attempts.

## Integrations

### Framework

```
Integration Registry → Adapter → Auth Layer → External Service
```

Lifecycle: `draft` → `connected` → `active` | `disabled` | `error`

Credentials are encrypted and never logged.

### GitHub Integration

**Implemented:**
- PAT verification via `GET https://api.github.com/user`
- Signed inbound webhooks at `POST /integrations/{id}/github/webhook`
- Events: `push`, `pull_request`, `workflow_run`
- CI/CD normalization via `GitHubActionsAdapter`

**Configure:**
1. `POST /integrations` with `provider: "github"`
2. `POST /integrations/{id}/connect` with PAT + optional `webhook_secret`
3. Point GitHub webhook to `/integrations/{id}/github/webhook`

## Automations

Trigger types: `event`, `github_event`, `schedule`, `deployment`

Action types: `start_workflow`, `send_webhook`, `create_notification`, `generate_recommendation`

High-impact actions (`start_workflow`, `send_webhook`) require approval by default.

Templates available at `GET /automations/templates`.

## API Keys

Extended scopes:

- `requests:read`, `requests:write`
- `workflows:read`, `workflows:execute`
- `webhooks:manage`, `integrations:manage`, `automations:manage`
- `events:read`

Rotation: `POST /api-keys/{id}/rotate` — revokes old key, returns new secret once.

Activity tracking: `last_used_at`, `last_used_ip` (privacy-compliant, truncated).

## Dashboards

- `/developers` — portal overview
- `/webhooks` — endpoint management
- `/integrations` — connected services
- `/automations` — triggers and executions

## CLI

```bash
modelbridge events list --json
modelbridge events catalog --json
modelbridge webhooks list --json
modelbridge webhooks create --name "Alerts" --url https://example.com/hook --events request.completed
modelbridge integrations list --json
modelbridge automations list --json
```

## Metrics

- `modelbridge_webhook_deliveries_total{status}`
- `modelbridge_webhook_retry_total`
- `modelbridge_webhook_delivery_failures_total`
- `modelbridge_integration_requests_total{provider,status}`

## Security Review

| Risk | Mitigation |
|------|------------|
| Webhook SSRF | URL validation + DNS resolution checks |
| Secret exposure | Encrypt at rest; one-time display |
| External event forgery | HMAC signature verification |
| Cross-tenant access | Organization-scoped queries |
| Automation privilege escalation | Approval gates; org-scoped workflows |
| API key scope bypass | Scope validation on gateway + RBAC on management APIs |

## Known Limitations

- `send_webhook` automation action queues delivery metadata only (uses configured webhook_id)
- Schedule triggers require worker cron (existing workflow scheduler pattern)
- Additional CI/CD providers (GitLab, CircleCI) have adapter interfaces but are not yet implemented
- GitHub integration requires manual webhook configuration in GitHub settings
