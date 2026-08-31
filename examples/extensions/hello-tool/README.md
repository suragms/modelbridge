# Hello Tool Extension

Reference extension for ModelBridge Phase 10.

## Manifest

See `manifest.json` for the full plugin manifest schema.

## Security

This extension declares `tool_execution` permission only. It does not request network or database access.

## Installation

1. Publish the manifest via `POST /extensions/publish` (admin)
2. Install with explicit permission approval via `POST /extensions/installations`
3. Enable with `POST /extensions/installations/{id}/enable`

The reference handler is built into ModelBridge at `app.services.extensions.tools.HelloToolPlugin` — trusted entry-point loading is required for third-party pip packages.

## Lifecycle Hooks

Tool extensions support `on_install`, `on_enable`, `on_disable`, and `on_uninstall` via the `IntegrationPlugin` interface when implemented as Python packages.
