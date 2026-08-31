# Plugin Architecture

ModelBridge supports **trusted provider plugins** installed by administrators.

> Phase 10 adds the full extension ecosystem (manifests, registry, templates, permissions). See [extensions.md](./extensions.md).

## Plugin Types

| Category | Status |
|----------|--------|
| Provider plugins | Implemented |
| Tool extensions | Implemented (manifest + trusted handlers) |
| Agent/workflow templates | Implemented |
| Integration extensions | Architecture + manifest type |
| Auth plugins | Planned |
| Routing plugins | Planned |

## Provider Plugin Interface

```python
from app.plugins.base import ProviderPlugin, ProviderPluginInfo
from app.providers.base import AIProvider

class MyProviderPlugin(ProviderPlugin):
    info = ProviderPluginInfo(name="myprovider", version="1.0.0", description="Custom provider")

    def create_provider(self, api_key=None, base_url=None, **kwargs) -> AIProvider:
        return MyProvider(api_key=api_key, base_url=base_url)
```

## Discovery

Plugins register via Python entry points:

```toml
[project.entry-points."modelbridge.providers"]
myprovider = "my_package.plugin:MyProviderPlugin"
```

## Lifecycle

1. **Install** — pip install the plugin package
2. **Discover** — entry points scanned at gateway startup
3. **Validate** — must implement `ProviderPlugin`
4. **Initialize** — plugin instance created
5. **Enable** — type available in provider registry
6. **Disable** — remove entry point and restart

## Security

- Plugins are **trusted code** installed by administrators
- ModelBridge does **not** execute arbitrary remote/untrusted plugins
- Failed plugins are logged and skipped — they do not crash the gateway

## Minimal Example

See `examples/` and built-in providers in `apps/api/app/providers/` for reference implementations.

## Diagnostics

Plugin load status is available via the plugin manager diagnostics API internally. Failed loads are recorded with safe error messages (no secrets).
