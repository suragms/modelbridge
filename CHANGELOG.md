# Changelog

All notable changes to ModelBridge are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- Phase 17 AI Quality Platform: evaluation pipelines, LLM judges, regression testing, production sampling, quality gates, scorecards, alerts, dashboard (`/quality`), CLI/SDK, and `docs/quality-platform.md`
- Phase 16 AI Studio: visual workflow builder, agent builder, prompt studio with versioning, playground, model comparison, evaluation framework, deployment pipelines, studio APIs, dashboard (`/studio`), CLI/SDK, metrics, and `docs/ai-studio.md`
- Phase 15 marketplace and community: verified publisher profiles, submission & review lifecycle, installation tracking, moderation/reviews, community contributor guide, `/marketplace` dashboard, CLI, and SDKs
- Phase 14 advanced developer platform: event bus, HMAC-signed webhooks with SSRF protection, third-party integrations, event-driven automations, scoped API keys, developer portal, and CLI/SDK APIs
- Phase 13 intelligence layer: operational analytics, provider/cost/capacity intelligence, anomaly detection, explainable recommendations, operations assistant, background jobs, dashboard, CLI/SDK, and `docs/intelligence.md`
- Phase 12 cloud architecture: regions, managed instance lifecycle, service discovery, scoped configuration, rollouts, usage metering, quotas, incidents, cloud onboarding, global health APIs, `/cloud` dashboard, CLI/SDK commands, Kubernetes HPA config, and `docs/cloud.md`
- Phase 11 enterprise collaboration: workspaces, projects, environments, config versioning, fleet management, control-plane APIs, dashboards, CLI, and SDKs
- Phase 10 extension ecosystem: manifests, registry, lifecycle, permissions, templates, private registries, admin UI, CLI/SDK, metrics, and reference hello-tool extension
- Phase 9 AI agent infrastructure: agent definitions, execution engine, tool registry, workflows, ARQ jobs, memory, observability, dashboard, CLI, and SDKs
- Phase 8 AI governance: policy engine, allow/block lists, PII/secret detection, redaction, approvals, dashboard, CLI/SDK APIs, reports, and Prometheus governance metrics
- Redis response-cache keys include policy fingerprints so policy changes cannot be bypassed by stale cache entries

## [1.0.0] - 2026-08-28

### Added

- Official CLI (`modelbridge`) with config, login, status, providers, models, chat, embeddings, analytics, requests, org, and benchmark commands
- Python SDK (`modelbridge-sdk`) with sync/async clients and streaming
- TypeScript SDK (`@modelbridge/sdk`) with chat, embeddings, streaming, and types
- Plugin architecture for trusted provider extensions via entry points
- Benchmark framework in CLI
- Example applications (python-chat, streaming-chat, rag-example)
- Documentation structure for getting started, guides, API, SDK, deployment
- GitHub community files (CODE_OF_CONDUCT, SUPPORT, issue/PR templates)
- Release automation workflow
- Semantic versioning strategy (`VERSION` file)

### Changed

- API version aligned to 1.0.0
- Production Docker image uses multi-stage non-root build

### Security

- CLI masks secrets in configuration output
- Plugin system loads only trusted entry-point plugins

[1.0.0]: https://github.com/suragms/modelbridge/releases/tag/v1.0.0
