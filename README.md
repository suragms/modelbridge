<div align="center">

# ModelBridge

> **One API. Every AI model.**

An open-source, self-hostable AI gateway and intelligent model router for cloud and local AI models.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-black.svg?logo=next.js)](https://nextjs.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](docker-compose.yml)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[Features](#features) · [Quick Start](#quick-start) · [API Usage](#api-usage) · [Providers](#supported-providers) · [Contributing](#contributing)

</div>

---

## Why ModelBridge?

Switching between AI providers means rewriting code, juggling API keys, and managing different rate limits and pricing. ModelBridge solves this with **a single OpenAI-compatible endpoint** that intelligently routes every request to the right model — whether it's running on OpenAI's cloud or your own machine with Ollama.

**100% open source** under Apache 2.0. Self-host it, audit it, extend it — your data never leaves your infrastructure unless you want it to.

## Features

- **OpenAI-Compatible API** — Drop-in replacement; use existing OpenAI SDKs and tools
- **Multi-Provider** — Ollama, OpenAI, Anthropic, Gemini, Groq, OpenRouter, LM Studio, and custom providers
- **Intelligent Routing** — Auto, balanced, cheapest, fastest, quality, local-only, privacy-first strategies
- **Fallback System** — Automatic failover when providers are unavailable
- **Usage Tracking** — Token counting, cost estimation, request logging
- **Observability & Analytics** — Request lifecycle tracking, real-time dashboards, Prometheus metrics, audit logging
- **Streaming** — Full SSE streaming support
- **Advanced AI Features**
  - Embeddings API (`POST /v1/embeddings`) with capability-aware routing
  - Tool/function calling with OpenAI-compatible normalization (gateway only — no auto-execution)
  - JSON mode and structured output routing
  - Vision/multimodal support with image URL security controls
  - Capability-aware routing (chat, tools, vision, embeddings, JSON)
- **AI Playground** — Interactive model testing at `/playground` with real gateway requests
- **Model Comparison** — Side-by-side comparison at `/playground/compare`
- **Production Features**
  - Multi-tenant organizations with membership and org switching
  - Role-based access control (OWNER, ADMIN, MEMBER, VIEWER)
  - API key scopes and expiration enforcement
  - Redis-backed rate limiting with standard headers
  - Token quotas and estimated cost budgets with in-app alerts
  - ARQ background jobs (provider health checks, data retention)
  - Production Docker (multi-stage, non-root) and Kubernetes manifests
- **AI Governance**
  - Policy engine (ALLOW / WARN / DENY / REQUIRE_APPROVAL / REDACT)
  - Model allowlists and blocklists; provider and API-key restrictions
  - Heuristic request/risk classification (not a compliance certification)
  - PII and secret detection with safe logging (values never stored)
  - Prompt/response redaction and heuristic content safety
  - Approval workflow with replay header (not silent background execution)
  - Governance audit trails, reports (JSON/CSV), dashboard, CLI, and SDKs
- **AI Agent Infrastructure**
  - Persistent agent definitions with organization isolation and resource limits
  - Agent execution runtime with multi-step model + tool loop via gateway
  - Secure built-in tool registry (no arbitrary code execution)
  - Workflow orchestration with validation, scheduling, and webhook triggers
  - Long-running jobs via ARQ workers with fallback inline execution
  - Human-in-the-loop pauses for high-risk tools (Phase 8 approvals)
  - Agent memory (execution, session, agent scopes) and execution traces
  - Agent observability, cost tracking, dashboard, CLI, and SDKs
- **ModelBridge Ecosystem**
  - Extension architecture with validated manifests and semver
  - Plugin lifecycle (install, enable, disable, uninstall) with explicit permissions
  - Local/private registry and package search
  - Provider, tool, integration, agent template, and workflow template types
  - Trust levels (official, verified, community, unverified)
  - Extension administration UI and template gallery
  - Extension SDK interfaces, CLI commands, and reference hello-tool extension
  - Plugin observability metrics and audit events
- **Enterprise Collaboration**
  - Team workspaces with membership and RBAC integration
  - Projects with optional restricted access
  - Development, staging, and production environments
  - Configuration versioning, comparison, promotion, and rollback
  - Activity timelines for workspaces and projects
  - Fleet management with instance registration and heartbeats
  - Control-plane APIs for configuration and policy distribution
  - Enterprise and fleet dashboards
- **Cloud & Global Scale**
  - Control-plane / data-plane architecture (metadata and APIs)
  - Region metadata and region-aware routing (with data residency filters)
  - Managed instance lifecycle (provisioning through decommission)
  - Service discovery registry and health aggregation
  - Scoped configuration (global → org → workspace → project → environment)
  - Multi-region configuration rollouts with verification
  - Usage metering events and quota enforcement foundation
  - Cloud operations dashboard (`/cloud`)
  - CLI and SDK cloud/usage commands
  - Kubernetes manifests with HPA readiness (validated structure)
- **AI Intelligence Layer**
  - Operational intelligence from real request, cost, and health telemetry
  - Provider performance analysis with explainable recommendations
  - Cost intelligence (actual vs estimated) and trend forecasting
  - Capacity analysis and anomaly detection (z-score)
  - Recommendation lifecycle with human approval workflows
  - Operations assistant for authorized NL queries
  - Intelligence dashboard (`/intelligence`) and CLI/SDK support
- **Developer Platform (Phase 14)**
  - Event bus with catalog and organization-scoped persistence
  - Webhooks with HMAC signing, SSRF protection, retries, and delivery tracking
  - Integration framework with encrypted credentials
  - GitHub integration (PAT verify, signed inbound webhooks, CI/CD normalization)
  - Event-driven automations with templates and approval gates
  - Scoped API keys with rotation and last-used tracking
  - Developer portal (`/developers`), webhooks, integrations, and automations dashboards
  - CLI and SDK support for events, webhooks, integrations, automations
- **Marketplace & Community (Phase 15)**
  - Marketplace catalog built on the extension registry
  - Publisher profiles with verification states (unverified, verified, official)
  - Publishing workflow with automated validation and admin review
  - Version management and compatibility checks
  - Workflow, agent, integration, and template discovery
  - Installation tracking with history, updates, and rollback
  - Reviews, reporting, and moderation architecture
  - Marketplace dashboard (`/marketplace`) and contributor guide (`/community/contribute`)
  - CLI and SDK marketplace commands
- **Developer Platform (Phase 6)**
  - Official CLI (`modelbridge`) — chat, embeddings, analytics, org management
  - Python SDK (`modelbridge-sdk`) with sync/async and streaming
  - TypeScript SDK (`@modelbridge/sdk`)
  - Plugin architecture for provider extensions
  - Benchmark framework, examples, and release automation
- **Authentication** — JWT auth, API keys, role-based access
- **Multi-Tenant** — Organizations with per-org providers, keys, and analytics
- **Docker Ready** — One-command deployment with Docker Compose

## Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/suragms/modelbridge.git
cd modelbridge
cp .env.example .env
docker compose up -d
```

Open http://localhost:3000 to access the dashboard.

### Manual Setup

```bash
# Backend
cd apps/api
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Start PostgreSQL and Redis, then:
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend
cd ../web
npm install
npm run dev
```

## API Usage

Point any OpenAI SDK at ModelBridge:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="your-modelbridge-api-key"
)

response = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

### Streaming

```python
stream = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

## Supported Providers

| Provider | Chat | Streaming | Embeddings | Tools |
|----------|------|-----------|------------|-------|
| Ollama | ✅ | ✅ | ✅ | ❌ |
| OpenAI | ✅ | ✅ | ✅ | ✅ |
| Anthropic | ✅ | ✅ | ❌ | ✅ |
| Gemini | ✅ | ✅ | ✅ | ✅ |
| Groq | ✅ | ✅ | ❌ | ✅ |
| OpenRouter | ✅ | ✅ | ❌ | ✅ |
| LM Studio | ✅ | ✅ | ❌ | ❌ |
| Custom OpenAI-Compatible | ✅ | ✅ | Varies | Varies |

## Routing Strategies

- **Auto/Balanced** — Weighted scoring across quality, speed, cost, and reliability
- **Priority** — User-defined model priority order
- **Cheapest** — Lowest estimated cost
- **Fastest** — Lowest recent latency
- **Quality** — Highest quality score
- **Local Only** — Only local providers (Ollama, LM Studio)
- **Privacy First** — Prefer local and trusted providers
- **Round Robin** — Distribute requests evenly

## Configuration

Environment variables (see [`.env.example`](.env.example)):

```bash
DATABASE_URL=postgresql+asyncpg://modelbridge:modelbridge@localhost:5432/modelbridge
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=your-secret-here
ENCRYPTION_KEY=your-encryption-key
```

## Observability

- ✓ Request tracking with unique IDs and lifecycle statuses
- ✓ Token usage tracking (provider-reported, estimated, or unavailable)
- ✓ Estimated cost tracking with pricing registry
- ✓ Provider and model performance monitoring
- ✓ Request explorer with server-side filtering
- ✓ Analytics dashboard with real data charts
- ✓ Prometheus metrics at `/metrics`
- ✓ Audit logging for administrative actions
- ✓ OpenTelemetry-ready tracing abstraction

See [docs/observability.md](docs/observability.md) for details.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /v1/chat/completions` | Chat completions (OpenAI-compatible) |
| `GET /v1/models` | List available models |
| `POST /auth/register` | Create account |
| `POST /auth/login` | Sign in |
| `GET /providers` | List providers |
| `POST /providers` | Add provider |
| `GET /analytics/overview` | Analytics overview |
| `GET /analytics/requests` | Requests time series |
| `GET /logs` | Request logs (filterable) |
| `GET /logs/{request_id}` | Request detail |
| `GET /metrics` | Prometheus metrics |
| `GET /audit` | Audit logs |
| `GET /health` | Health check |

Interactive docs are available at [`/docs`](http://localhost:8000/docs) (Swagger) and [`/redoc`](http://localhost:8000/redoc) when the API is running.

## Architecture

```
                     ┌── Ollama
                     ├── OpenAI
                     ├── Gemini
                     ├── Claude
Application ──► ModelBridge ──┼── Groq
                     ├── OpenRouter
                     ├── LM Studio
                     └── Custom Provider
```

### Project Structure

```
modelbridge/
├── apps/
│   ├── api/          # FastAPI backend (auth, routing, providers, analytics)
│   └── web/          # Next.js dashboard
├── packages/shared/  # Shared packages
├── infrastructure/   # Docker infrastructure files
└── tests/            # E2E, integration, and unit tests
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.x (async) |
| Database | PostgreSQL 16, Redis 7 |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS 4 |
| Auth | JWT (HS256), bcrypt, Fernet encryption |
| Infra | Docker, Alembic, structlog, Prometheus |

## Roadmap

- [ ] Embedding support
- [ ] RAG integration
- [ ] Kubernetes manifests
- [ ] Advanced RBAC
- [ ] Webhook notifications
- [ ] Model comparison playground
- [ ] CLI tool
- [ ] Carbon-aware routing

## Contributing

🤝 **Contributions are always open!** Whether it's a bug fix, new provider, docs improvement, or just an idea — everyone is welcome, anytime. No contribution is too small.

1. Read [CONTRIBUTING.md](CONTRIBUTING.md)
2. Fork the repository and create your branch from `main`
3. Make your changes and add tests where possible
4. Run lint and tests locally:

```bash
cd apps/api
ruff check .
ruff format --check .
pytest
```

5. Submit a pull request

Found a security issue? Please see [SECURITY.md](SECURITY.md) for responsible disclosure.

## License

ModelBridge is **open source** under the [Apache License 2.0](LICENSE) — free to use, modify, and distribute, including commercially.

## Follow Me

Stay updated with ModelBridge development:

- 💻 **GitHub** — [@suragms](https://github.com/suragms)
- 💼 **LinkedIn** — [suragsunil](https://linkedin.com/in/suragsunil)
- 📸 **Instagram** — [@surag_sunil](https://instagram.com/surag_sunil)

---

<div align="center">

**Made with ❤️ by the ModelBridge community**

⭐ Star the repo · 🍴 Fork it · 🤝 Contributions always open

👉 **Follow [@suragms](https://github.com/suragms) for updates!**

</div>
