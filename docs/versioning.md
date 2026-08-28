# Versioning Strategy

ModelBridge uses **Semantic Versioning (SemVer)** for the entire project:

```
MAJOR.MINOR.PATCH
```

Example: `v1.0.0`

## Single Source of Truth

The canonical version lives in the repository root:

```
VERSION
```

All packages derive from this file:

| Component | Location |
|-----------|----------|
| API | `apps/api/pyproject.toml` (synced at release) |
| Web | `apps/web/package.json` (synced at release) |
| CLI | `packages/cli/pyproject.toml` |
| Python SDK | `packages/python-sdk/pyproject.toml` |
| TypeScript SDK | `packages/typescript-sdk/package.json` |

## Version Meaning

- **MAJOR** — Breaking API, migration, or compatibility changes
- **MINOR** — New features, backward compatible
- **PATCH** — Bug fixes, documentation, non-breaking improvements

## Release Tags

Git tags use the format:

```
v1.0.0
```

Docker images (when published):

```
modelbridge/modelbridge-api:v1.0.0
modelbridge/modelbridge-api:latest
```

## Pre-1.0 Policy

While below `v1.0.0`, minor versions may include breaking changes with migration notes in `CHANGELOG.md`.
