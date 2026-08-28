# Production Deployment

ModelBridge Phase 5 adds multi-tenant organizations, RBAC, rate limiting, quotas, budgets, and background jobs.

## Organizations

- Users can belong to multiple organizations via `organization_members`
- Active organization is stored in JWT `org_id` claim or `X-Organization-ID` header
- Resources (providers, API keys, routing policies, logs) are scoped by `organization_id`

## RBAC Roles

| Role | Capabilities |
|------|-------------|
| OWNER | Full org control including delete |
| ADMIN | Manage providers, routing, keys, members, settings |
| MEMBER | Playground, analytics, create keys |
| VIEWER | Read-only analytics and audit |

## API Key Scopes

- `chat:write`, `embeddings:write`, `models:read`, `analytics:read`, `providers:read`
- Empty scopes = full gateway access (backward compatible)
- Expired keys are rejected at authentication

## Rate Limiting

Redis-backed limits per organization, API key, user, and IP.

Response headers:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`

Returns HTTP 429 when exceeded.

## Quotas & Budgets

- Monthly token quotas (organization and per API key)
- Estimated cost budgets with warning alerts at configurable thresholds
- **All cost limits use estimated data — not exact provider billing**

## Background Jobs

Run the ARQ worker:

```bash
cd apps/api
arq app.jobs.worker.WorkerSettings
```

Jobs:
- `provider_health_checks` — scheduled provider health polling
- `data_retention_cleanup` — removes expired request logs and audit entries

## Production Configuration

Required in production (`ENVIRONMENT=production`):

- `JWT_SECRET` — secure random value
- `ENCRYPTION_KEY` — Fernet key for provider credentials
- `DATABASE_URL`
- `REDIS_URL`
- `CORS_ORIGINS` — explicit origins (no `*`)

## Docker

```bash
docker compose -f docker-compose.yml up -d --build
docker compose -f docker-compose.yml up -d worker
```

## Kubernetes

See `infrastructure/k8s/` for manifests including API, web, worker, ingress, and HPA templates.

## Backup & Recovery

PostgreSQL backup (manual):

```bash
pg_dump -Fc -h localhost -U modelbridge modelbridge > modelbridge.backup
```

Restore:

```bash
pg_restore -d modelbridge -c modelbridge.backup
```

Run migrations after restore:

```bash
cd apps/api && alembic upgrade head
```

Automatic backups are **not** included — configure your platform (RDS, Cloud SQL, etc.) separately.

## Member Invitations

Invite tokens are generated via `POST /organizations/current/invites`. Share the returned token URL manually — **email delivery is not implemented**.

## Known Limitations

- Playground uses JWT auth; rate limits apply via org settings when configured
- Global routing policies (null `organization_id`) remain for backward compatibility
- Budget alerts are in-app records only (no email/Slack)
