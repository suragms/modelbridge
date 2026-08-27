# ModelBridge

> **One API. Every AI model.**

ModelBridge is an open-source, self-hostable AI gateway and intelligent model router for cloud and local AI models.

## Features

- **OpenAI-Compatible API** — Use existing OpenAI SDKs and tools
- **Multi-Provider** — Ollama, OpenAI, Anthropic, Gemini, Groq, OpenRouter, LM Studio, and custom providers
- **Intelligent Routing** — Auto, balanced, cheapest, fastest, quality, local-only, privacy-first strategies
- **Fallback System** — Automatic failover when providers are unavailable
- **Usage Tracking** — Token counting, cost estimation, request logging
- **Analytics Dashboard** — Monitor usage, latency, costs, and provider health
- **Streaming** — Full SSE streaming support
- **Tool Calling** — Function/tool calling support for compatible models
- **Authentication** — JWT auth, API keys, role-based access
- **Docker Ready** — One-command deployment with Docker Compose

## Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/yourusername/modelbridge.git
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

Environment variables (see `.env.example`):

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

## Roadmap

- [ ] Anthropic Claude provider
- [ ] Google Gemini provider
- [ ] Embedding support
- [ ] RAG integration
- [ ] Kubernetes manifests
- [ ] Advanced RBAC
- [ ] Webhook notifications
- [ ] Model comparison playground
- [ ] CLI tool
- [ ] Carbon-aware routing

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
