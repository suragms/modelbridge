# Contributing to ModelBridge

Thank you for your interest in contributing to ModelBridge!

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 16+
- Redis 7+
- Docker (optional)

### Local Development

```bash
# Clone the repository
git clone https://github.com/suragms/modelbridge.git
cd modelbridge

# Backend setup
cd apps/api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"

# CLI and Python SDK (optional)
pip install -e ../../packages/cli
pip install -e ../../packages/python-sdk

# Start database services
docker compose -f ../../docker-compose.dev.yml up postgres redis -d

# Run migrations
alembic upgrade head

# Start the API
uvicorn app.main:app --reload --port 8000

# Frontend setup (new terminal)
cd ../web
npm install
npm run dev
```

### Running Tests

```bash
# API tests
cd apps/api && pytest tests/ -v

# CLI tests
pytest packages/cli/tests/ -v

# Python SDK tests
pytest packages/python-sdk/tests/ -v

# Frontend build
cd apps/web && npm run build
```

### Docker Development

```bash
docker compose -f docker-compose.dev.yml up
```

## Adding a Provider

1. Create a new directory in `apps/api/app/providers/your_provider/`
2. Implement the `AIProvider` base class from `app/providers/base.py`
3. Register your provider in `app/providers/registry.py`
4. Add the provider type to the `ProviderType` enum in `app/models/provider.py`
5. Write tests in `apps/api/tests/`

```python
from app.providers.base import AIProvider, ChatCompletionResult, ProviderModel

class YourProvider(AIProvider):
    provider_type = "your_provider"

    async def chat_completion(self, model, messages, **kwargs):
        # Implement chat completion
        ...

    async def stream_completion(self, model, messages, **kwargs):
        # Implement streaming
        ...

    async def list_models(self):
        # Return available models
        ...

    async def health_check(self):
        # Check provider health
        ...
```

## Adding a Routing Strategy

1. Create a new file in `apps/api/app/router/strategies/`
2. Implement the strategy function
3. Register it in `app/router/engine.py`

## Running Tests

```bash
cd apps/api
python -m pytest tests/ -v
```

## Code Style

- Use `ruff check .` for linting
- Use `ruff format .` for formatting
- Add type hints to all functions
- Follow existing patterns in the codebase

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## Issue Templates

- **Bug Report**: Report a bug
- **Feature Request**: Suggest a new feature
- **Provider Request**: Request support for a new AI provider
- **Security Issue**: Report a security vulnerability (see SECURITY.md)
