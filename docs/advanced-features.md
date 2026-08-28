# Advanced AI Features

ModelBridge Phase 4 adds developer-focused advanced capabilities on top of the Phase 3 observability layer.

## Embeddings API

```http
POST /v1/embeddings
```

```json
{
  "model": "auto",
  "input": ["First document", "Second document"]
}
```

- OpenAI-compatible response format
- Capability-aware routing (only embedding-capable models)
- Request tracking without storing input content by default

## Tool / Function Calling

- OpenAI-compatible `tools` and `tool_choice` parameters
- Capability-aware routing (only tool-capable models)
- Normalized tool call responses across providers
- **ModelBridge does not execute client tools** — it is a gateway

## Structured Output / JSON Mode

- Supports `response_format: { "type": "json_object" }`
- Distinguishes JSON mode vs structured schema enforcement
- Routes only to models with `json_mode` / `structured_output` capabilities

## Vision / Multimodal

- OpenAI-compatible multimodal message content
- Automatic vision capability detection
- Image URL validation (HTTPS and data URIs only; blocks private/internal hosts)
- Does not download arbitrary URLs

## Capability-Aware Routing

The router detects required capabilities from each request:

```
Incoming Request → Detect Capabilities → Filter Models → Apply Policy → Select Model
```

Capabilities include: `chat`, `streaming`, `embeddings`, `tools`, `vision`, `json_mode`, `structured_output`.

## AI Playground

Dashboard routes:

- `/playground` — interactive chat testing with real API calls
- `/playground/compare` — side-by-side model comparison

Playground APIs:

- `POST /playground/chat`
- `POST /playground/compare`

Both use the same authentication, routing, usage tracking, and observability systems as external API requests.

## Routing Debugger

The `/routing` page shows:

- Requested capabilities
- Compatible models
- Filtered models with reasons (e.g. "Does not support Vision")

## Security

- Image URLs validated before forwarding to providers
- SSRF protection for private/internal hosts
- Secrets never stored in request logs or playground metadata
- Tool definitions are forwarded to providers but never executed by ModelBridge

## Known Limitations

- Capability inference from model IDs is conservative; sync models from providers for best accuracy
- Structured schema enforcement depends on underlying provider support
- Streaming in the playground uses `/v1/chat/completions` directly
- Ollama tool calling support varies by model
