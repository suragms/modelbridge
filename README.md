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
- **Analytics Dashboard** — Monitor usage, latency, costs, and provider health
- **Streaming** — Full SSE streaming support
- **Tool Calling** — Function/tool calling support for compatible models
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

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /v1/chat/completions` | Chat completions (OpenAI-compatible) |
| `GET /v1/models` | List available models |
| `POST /auth/register` | Create account |
| `POST /auth/login` | Sign in |
| `GET /providers` | List providers |
| `POST /providers` | Add provider |
| `GET /analytics/summary` | Usage summary |
| `GET /logs` | Request logs |
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

- **GitHub** — [@suragms](https://github.com/suragms)
- **X (Twitter)** — [@suragms](https://x.com/suragms)
- **LinkedIn** — [suragms](https://linkedin.com/in/suragms)

---

<div align="center">

**Made with ❤️ by the ModelBridge community**

⭐ Star the repo · 🍴 Fork it · 🤝 Contributions always open

👉 **Follow [@suragms](https://github.com/suragms) for updates!**

</div>
