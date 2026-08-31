# ModelBridge Marketplace

Phase 15 adds a community marketplace built on the Phase 10 extension registry.

## Architecture

```
Publisher → Submission → Validation → Security Checks → Compatibility → Registry → Discovery → Installation
```

Marketplace items wrap `extension_packages` with catalog metadata (status, visibility, slug, featured, analytics).

## Content Types

| Type | Source plugin_type |
|------|-------------------|
| extension | provider, tool |
| integration | integration |
| agent | agent_template |
| workflow | workflow_template |
| template | generic templates |

## Publisher Verification

| Status | Meaning |
|--------|---------|
| unverified | Default for new publishers |
| verified | Administratively verified |
| official | ModelBridge-maintained |

Verification is **never automatic** — only admins can upgrade publisher status.

## Publishing Workflow

1. **Draft** — Create via `POST /marketplace/items` with manifest JSON
2. **Validate** — Automated manifest, compatibility, dependency, and secret scanning
3. **Submit** — `POST /marketplace/items/{id}/submit`
4. **Review** — Admin approves via `POST /admin/marketplace/items/{id}/publish`
5. **Published** — Visible in discovery (subject to visibility rules)

## Package Validation

Automated checks:
- Required manifest fields
- Semver version format
- Plugin type validity
- Permission whitelist
- ModelBridge version compatibility
- Dependency structure
- Embedded secret detection

Security review states: `not_reviewed`, `automated_passed`, `automated_failed`, `manual_review`, `approved`

## Visibility

| Level | Access |
|-------|--------|
| public | All authenticated users (when published) |
| organization | Owning organization only |
| private | Owning organization only |

## Installation

```
POST /marketplace/items/{id}/install
{
  "approved_permissions": ["tool_execution"],
  "enable": true
}
```

Installation validates compatibility and permissions before delegating to the extension lifecycle service. History is tracked in `marketplace_install_history`.

## Updates and Rollback

- **Update**: Changes `package_version_id` on existing installation, records history
- **Rollback**: Restores `previous_version_id` when available (version pointer swap only — no stateful migration rollback)

## Trust Signals

Displayed on item pages (never fabricated):
- Publisher verification status
- Official content (`trust_level: official`)
- Security review status
- Real install counts from analytics events
- Version compatibility requirements

## Reviews and Reports

- Reviews: One per user per org per item (`POST /marketplace/items/{id}/reviews`)
- Reports: Moderation queue for admins (`POST /marketplace/items/{id}/report`)

## CLI

```bash
modelbridge marketplace search --query "agent"
modelbridge marketplace list --json
modelbridge marketplace info research-agent
modelbridge marketplace install research-agent --permissions tool_execution,ai_provider_access
```

## Metrics

- `modelbridge_marketplace_installations_total{content_type}`
- `modelbridge_marketplace_validation_failures_total`
- `modelbridge_marketplace_publications_total{content_type}`

## Known Limitations

- No remote/cloud marketplace sync (local registry only)
- No cryptographic package signing (architecture placeholder only)
- No automated publisher verification
- Popularity ranking uses real install counts only (no fabricated metrics)
- Reviews require authenticated org members; no public anonymous ratings

## Governance

See [CONTRIBUTING.md](../CONTRIBUTING.md) and [SECURITY.md](../SECURITY.md) for contribution and security advisory processes.
