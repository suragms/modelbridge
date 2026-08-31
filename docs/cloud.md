# ModelBridge Cloud Architecture (Phase 12)

This document describes the managed cloud architecture for ModelBridge. Features are labeled as **Implemented**, **Architectural**, or **Planned**.

## Control Plane vs Data Plane

**Architectural**

```text
                    ModelBridge Cloud
                           │
                  ┌────────┴────────┐
                  │   Control Plane │
                  └────────┬────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
       Region A         Region B         Region C
          │                │                │
      Data Plane       Data Plane       Data Plane
```

| Layer | Responsibilities | Implemented |
|-------|------------------|-------------|
| **Control plane** | Organizations, users, workspaces, projects, policies, instance registry, region metadata, configuration rollouts | Partial — unified deployment exposes control APIs; separate physical control plane is **Architectural** |
| **Data plane** | API requests, routing, providers, caching, agents, workflows | **Implemented** in self-hosted and registered fleet instances |

Inference traffic is **not** routed through the control plane by default.

## Regions

**Implemented**

- Persistent `regions` table with `code`, `status` (`active`, `degraded`, `disabled`), `capabilities`, and `data_residency_zones`
- Default `local` region seeded at startup for self-hosted deployments
- APIs: `GET/POST/PATCH /cloud/regions`
- Region-aware routing filters in `RouteService.plan()` when `region_code` or residency policy is supplied

**Architectural**

- Physical multi-region infrastructure (requires genuine deployment per region)

## Data Residency

**Implemented**

- Policies: `global`, `eu_only`, `us_only`, `india_only`
- Enforced only when provider `data_residency` / `region` metadata or region `data_residency_zones` match
- Limitation: without explicit metadata, residency cannot be legally guaranteed

## Managed Instance Lifecycle

**Implemented**

States: `provisioning` → `active` → `updating` / `degraded` / `failed` → `decommissioned`

- Extended `managed_instances` with `lifecycle_status`, `region_id`, `plane_type`
- Cloud APIs: `POST /cloud/instances`, lifecycle transitions, heartbeats update lifecycle
- All transitions recorded in activity events

## Service Discovery

**Implemented**

- `service_registrations` table and `ServiceDiscovery` abstraction
- Local API self-registers on startup in the deployment region
- Endpoint resolution falls back to local settings when registry is empty

**Planned**

- Automatic cross-region registration from deployed data planes

## Configuration Scopes

**Implemented**

Precedence (later overrides earlier):

```text
Global → Organization → Workspace → Project → Environment
```

- `scoped_configurations` table with versioning
- `GET /cloud/config/resolved` merges active configs
- `POST /cloud/config/{id}/rollout` creates verified rollouts per region

## High Availability

**Implemented**

- Stateless API with multiple replicas (Docker Compose / Kubernetes)
- `/health` (liveness) and `/ready` (readiness) with database and Redis checks
- Kubernetes manifest: 2+ API replicas, HPA on CPU

**Architectural**

- Automatic failover between regions (requires load balancer + health checks + registry)

## Failover

**Implemented**

- `failover_events` table and `FailoverService` for recording verified failovers
- Health-based target selection from service registry

**Architectural**

- Automatic production failover without operator-configured infrastructure

## Usage Metering

**Implemented**

- Append-only `usage_meter_events` (requests, tokens, agent/workflow execution types)
- Gateway records request/token events on successful chat and embedding calls
- `GET /usage/summary` aggregation by organization and period
- Prometheus metrics: `modelbridge_managed_instances_total`, `modelbridge_configuration_rollouts_total`, etc.

**Planned**

- Billing calculations (requires pricing rules)

## Quotas

**Implemented**

- Per-organization quotas (`requests`, `tokens`, `agent_executions`, `concurrent_executions`)
- Gateway enforces request quotas (HTTP 429 when exceeded)
- `GET/PUT /quotas`

## Incidents

**Implemented**

- Manual incident records (`open`, `investigating`, `mitigated`, `resolved`)
- APIs under `/cloud/incidents`
- No automatic fake incident generation

## Cloud Onboarding

**Implemented**

- `cloud_onboarding` persistence with step tracking
- `POST /cloud/onboarding/bootstrap` creates workspace, project, and default environments
- Region selection and residency policy stored on completion

## Tenant Isolation

**Implemented**

- All cloud APIs scoped by `organization_id` from auth context
- Cross-organization resource access returns 403/404
- Usage and quota data isolated per organization

## Backup & Disaster Recovery

**Architectural / Documented**

| Item | Self-hosted guidance |
|------|---------------------|
| **Backup scope** | PostgreSQL (all metadata, metering, config), Redis optional (cache only) |
| **Frequency** | Daily minimum for production; continuous WAL archiving recommended |
| **Retention** | 30 days minimum; align with audit retention settings |
| **Verification** | Restore to staging and run API test suite |
| **RPO/RTO** | Depends on backup tooling — not measured by ModelBridge itself |

Core correctness does not depend on Redis; cache/queue failures degrade gracefully via `resilience.py`.

## Kubernetes

**Implemented** (manifest structure validated)

- See `infrastructure/k8s/modelbridge.yaml`
- Deployments, Services, ConfigMaps, Secret references, probes, resource limits, HPA
- Secrets use placeholder values — replace before production

## CLI & SDK

```bash
modelbridge cloud health
modelbridge cloud regions list
modelbridge cloud instances list
modelbridge usage summary
```

Python: `client.cloud.*`, `client.usage.*`  
TypeScript: `client.cloud.*`, `client.usage.*`

## Known Limitations

1. Physical global regions are metadata unless you deploy and register instances per region.
2. Data residency enforcement requires provider/region metadata configuration.
3. Configuration rollout verification is control-plane local (instance ack **Planned**).
4. Autoscaling HPA manifest is structural — validate metrics server in your cluster.
5. Billing is not implemented — metering foundation only.

## Recommended Phase 13

- Managed billing integration and invoice generation
- Cross-region automatic failover with verified traffic shifting
- Instance-acknowledged configuration rollout and atomic fleet rollback
- Read replica routing for analytics queries
- Agent/workflow project/environment FK binding
