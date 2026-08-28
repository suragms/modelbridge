# Python SDK

Install from source (PyPI publishing requires explicit release configuration):

```bash
pip install -e packages/python-sdk
```

## Usage

```python
from modelbridge import ModelBridge

client = ModelBridge(
    base_url="http://localhost:8000",
    api_key="mb_YOUR_KEY",
)

# Chat
response = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "Hello!"}],
)

# Streaming
for chunk in client.chat.completions.stream(
    model="auto",
    messages=[{"role": "user", "content": "Hello!"}],
):
    delta = chunk["choices"][0]["delta"].get("content")
    if delta:
        print(delta, end="")

# Embeddings
emb = client.embeddings.create(model="auto", input="Hello world")
```

## Async

```python
from modelbridge import AsyncModelBridge

async def main():
    client = AsyncModelBridge(base_url="http://localhost:8000", api_key="mb_KEY")
    async for chunk in client.chat.completions.stream(
        model="auto",
        messages=[{"role": "user", "content": "Hi"}],
    ):
        print(chunk)
```

## Configuration

| Parameter | Description |
|-----------|-------------|
| `base_url` | ModelBridge API URL |
| `api_key` | Gateway API key |
| `token` | JWT for dashboard endpoints |
| `timeout` | Request timeout (seconds) |
| `org_id` | Active organization ID |
