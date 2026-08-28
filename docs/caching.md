# Response Caching

ModelBridge caches exact-match responses in Redis to reduce provider latency and cost for repeated requests.

## Overview

| Endpoint | Cacheable | Default TTL |
|----------|-----------|-------------|
| `POST /v1/chat/completions` | Non-streaming, no tools | 1 hour |
| `POST /v1/embeddings` | Always (when enabled) | 24 hours |

Streaming requests, tool-calling requests, and requests with explicit tool choice are **never cached**.

## Configuration

Environment variables (see `.env.example`):

```bash
CACHE_ENABLED=true
CACHE_KEY_PREFIX=mb:cache
CHAT_CACHE_TTL_SECONDS=3600
EMBEDDING_CACHE_TTL_SECONDS=86400
SEMANTIC_CACHE_ENABLED=false
```

## Cache Policies

Set via the `X-ModelBridge-Cache-Policy` header:

| Policy | Behavior |
|--------|----------|
| `default` | Read from cache on hit; write on miss |
| `no_cache` | Skip cache entirely |
| `bypass_cache` | Skip read; still write on success |
| `force_cache` | Only serve from cache; return 412 on miss |

Example:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $API_KEY" \
  -H "X-ModelBridge-Cache-Policy: default" \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","messages":[{"role":"user","content":"Hello"}]}'
```

## Cache Keys

Keys are SHA-256 hashes of:

- Organization ID (tenant isolation)
- Requested model
- Message content and generation parameters
- Endpoint type (chat vs embeddings)

Identical requests from the same organization return the same cached response.

## Observability

Prometheus metric `modelbridge_cache_events_total` tracks:

- `hit` — cache served a response
- `miss` — key not found
- `write` — response stored
- `bypass` — policy skipped read
- `error` — Redis unavailable (gateway continues without cache)

## Semantic Cache (Future)

Semantic caching (similarity-based matching) is defined in `app/services/semantic_cache.py` but **disabled by default** via `SEMANTIC_CACHE_ENABLED=false`. No fabricated semantic matches are returned.

## Provider Prompt Caching

Models that support provider-native prompt caching (e.g. Anthropic, OpenAI) expose the `prompt_caching` capability via `ModelCapability` rows or provider type detection. This is separate from ModelBridge's response cache.

## Security

- Cache entries are scoped by organization ID
- Secrets and API keys are never stored in cache values
- Redis failures degrade gracefully — requests proceed to providers
