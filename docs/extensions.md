# ModelBridge Extension Ecosystem

Phase 10 adds a secure extension architecture for providers, tools, integrations, and templates.

## Architecture

```text
ModelBridge Core
       │
       ├── Provider Extensions (entry-point plugins)
       ├── Tool Extensions (manifest + trusted handlers)
       ├── Integration Extensions (webhooks, external APIs)
       ├── Agent Templates (JSON definitions)
       └── Workflow Templates (validated node graphs)
```

Extensions are **not** arbitrary remote code execution. Trusted Python packages use setuptools entry points; templates are validated JSON; secrets are encrypted at rest.

## Plugin Types

| Type | Description |
|------|-------------|
| `provider` | AI provider via `ProviderPlugin` |
| `tool` | Agent tool with schema and permissions |
| `integration` | External system connector |
| `agent_template` | Reusable agent definition |
| `workflow_template` | Reusable workflow graph |

## Manifest

Every package requires a validated manifest:

```json
{
  "name": "hello-tool",
  "display_name": "Hello Tool",
  "description": "Reference tool",
  "version": "1.0.0",
  "plugin_type": "tool",
  "author": "Publisher",
  "license": "Apache-2.0",
  "minimum_modelbridge_version": "1.0.0",
  "permissions": ["tool_execution"]
}
```

## Permissions

| Permission | Meaning |
|------------|---------|
| `ai_provider_access` | May invoke gateway models |
| `network_access` | May call external URLs |
| `tool_execution` | May register executable tools |
| `database_access` | May use platform DB abstractions |
| `webhook_access` | May receive/send webhooks |

Administrators must explicitly approve permissions at install time.

## Lifecycle

```text
Discover → Validate → Check Compatibility → Review Permissions → Install → Enable
```

States: `installed`, `enabled`, `disabled`, `error`, `uninstalled`

Plugins are installed in `installed` state and require explicit enablement.

## Trust Levels

- **official** — shipped with ModelBridge
- **verified** — publisher verified (only when genuinely implemented)
- **community** — org-published packages
- **unverified** — default for new packages

## APIs

```
GET  /extensions/packages
POST /extensions/publish
GET  /extensions/installations
POST /extensions/installations
POST /extensions/installations/{id}/enable|disable
GET  /templates
POST /templates/installations/{id}/apply
```

## CLI

```bash
modelbridge extensions packages --type agent_template
modelbridge extensions install <version-id> --permissions tool_execution --enable
modelbridge extensions list
modelbridge templates list
```

## Security Model

- No untrusted code in the core API process
- Provider plugins: trusted pip packages + entry points only
- Tool plugins: manifest validation + reference handlers or entry points
- Templates: JSON only, parameter validation, no secrets in templates
- Configuration secrets encrypted via Fernet
- Organization isolation on all installations
- Governance applies to all extension-driven AI and tool actions

## Limitations

- No public cloud marketplace deployment (local/private registry only)
- No container-isolated extension runtime (documented for future work)
- Publisher verification is metadata-only unless manually set by admins
- Rollback tracks `previous_version_id` but is not fully automated

See also: [plugins.md](./plugins.md) for provider plugin development.
