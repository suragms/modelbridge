# Enterprise Collaboration & Control Plane

Phase 11 adds team workspaces, projects, environments, configuration versioning, and multi-instance fleet management.

## Hierarchy

```text
Organization → Workspace → Project → Environment
```

## Workspaces

Collaborative team areas with membership roles: `owner`, `admin`, `member`, `viewer`.

## Projects

Organize agents, workflows, and configurations. Restricted projects require explicit project membership even for workspace members.

## Environments

Each new project gets default environments:

- **Development** — unprotected
- **Staging** — unprotected
- **Production** — protected (`is_protected`)

Environment configuration is versioned with secret references (not raw secrets).

## Configuration Lifecycle

1. Create configuration version for an environment
2. Compare versions (secrets redacted in diffs)
3. Promote dev → staging → production with validation
4. Deploy with idempotency and verification
5. Rollback to a prior version (creates new version)

## Fleet / Control Plane

Register remote ModelBridge instances:

```bash
POST /fleet/register
```

Returns a one-time bearer credential. Instances authenticate via:

```text
Authorization: Bearer <credential>
```

Control-plane endpoints:

- `POST /control-plane/instances/{id}/heartbeat`
- `GET /control-plane/instances/{id}/configuration`
- `GET /control-plane/instances/{id}/policies`
- `POST /control-plane/instances/{id}/policies/report`

Local inference does **not** require control-plane availability.

## APIs

| Area | Prefix |
|------|--------|
| Workspaces | `/workspaces` |
| Projects | `/projects` |
| Environments | `/environments` |
| Enterprise overview | `/enterprise/overview` |
| Fleet | `/fleet` |
| Control plane | `/control-plane` |

## CLI

```bash
modelbridge workspaces list
modelbridge projects list --workspace-id <id>
modelbridge fleet list
modelbridge fleet status <instance-id>
```

## Security

- Organization isolation on all resources
- RBAC: `enterprise.read`, `enterprise.manage`, `fleet.read`, `fleet.manage`
- Instance credentials are hashed; plain token shown once at registration
- Activity timelines and config diffs never expose secrets
- Production promotion can require approval for protected environments

## Limitations

- No automatic production instance upgrades
- Deployment verification is local to control plane (instances report via heartbeat)
- Multi-instance metrics aggregation uses heartbeat snapshots only
- Rollback creates a new version; atomic cross-instance rollback is not guaranteed
