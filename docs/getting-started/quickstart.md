# Quickstart

Get ModelBridge running and send your first AI request in minutes.

## 1. Install

```bash
git clone https://github.com/suragms/modelbridge.git
cd modelbridge
cp .env.example .env
docker compose up -d
```

Open http://localhost:3000

## 2. Create an account

Register at `/register` or use the API:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"secure-password","full_name":"You"}'
```

## 3. Add a provider

In the dashboard, go to **Providers** → add Ollama or OpenAI → **Sync Models**.

## 4. Create an API key

Dashboard → **API Keys** → create a key. Copy it — shown once only.

## 5. First request

### cURL

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer mb_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### CLI

```bash
pip install -e packages/cli
modelbridge config set url http://localhost:8000
modelbridge config set api-key mb_YOUR_KEY
modelbridge chat "Hello!" --model auto
```

### Python SDK

```python
from modelbridge import ModelBridge

client = ModelBridge(base_url="http://localhost:8000", api_key="mb_YOUR_KEY")
response = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response["choices"][0]["message"]["content"])
```

## Next steps

- [Advanced features](../advanced-features.md)
- [Production deployment](../production.md)
- [CLI & SDK](../sdk/python.md)
