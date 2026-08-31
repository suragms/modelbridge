# AI Agent Infrastructure

Phase 9 adds a secure agent execution layer integrated with ModelBridge governance, routing, and observability.

## Overview

- **Agent definitions** — Organization-scoped agents with model config, tools, memory settings, and resource limits
- **Execution runtime** — Multi-step model + tool loop via the gateway (no governance bypass)
- **Tool registry** — Built-in safe tools only (`echo`, `current_time`, `json_format`); no arbitrary code execution
- **Workflows** — Deterministic node graph (start, agent, tool, condition, delay, approval, terminal)
- **Long-running jobs** — ARQ workers process agent/workflow executions asynchronously
- **Human-in-the-loop** — High-risk tools pause in `waiting_for_approval` (Phase 8 approval integration)
- **Memory** — Database-backed scopes: execution, session, agent
- **Observability** — Execution steps, Prometheus metrics, dashboard at `/agents` and `/workflows`

## Agent execution modes

| `model_configuration.execution_mode` | Behavior |
|----------------------------------------|----------|
| `gateway` (default) | Routes model calls through intelligent routing + governance |
| `direct` | Skips provider call; echoes last user message (testing only) |

## Resource limits

Every agent enforces:

- `max_steps` (default 10, capped at 100)
- `timeout_seconds` (default 300)
- Optional `max_tokens` and `max_budget_usd`

Executions stop safely when limits are reached.

## APIs

```
GET    /agents
POST   /agents
GET    /agents/{id}
PATCH  /agents/{id}
DELETE /agents/{id}
POST   /agents/{id}/execute
GET    /agents/executions/{id}
POST   /agents/executions/{id}/cancel
GET    /agents/overview
```

Workflow APIs under `/workflows` with activate, execute, schedules, and webhook triggers.

## CLI

```bash
modelbridge agents list
modelbridge agents get <id>
modelbridge agents execute <id> --input "Hello" --sync
modelbridge agents executions list
modelbridge workflows list
modelbridge workflows execute <id>
```

## SDK

```python
execution = client.agents.execute(agent_id="...", input_text="Hello", sync=True)
workflows = client.workflows.list()
```

## Webhook triggers

Create a trigger to receive a bearer secret. POST to `/workflows/triggers/{id}/webhook` with:

```
Authorization: Bearer <secret>
X-ModelBridge-Timestamp: <unix>
X-ModelBridge-Signature: <hmac-sha256>
```

## Limitations

- No visual drag-and-drop workflow builder (JSON/form-based definitions)
- Built-in tools only; custom tool handlers require server-side registration
- Vector/semantic memory is not enabled (database memory only)
- Approval resume for paused agent tool calls requires explicit continuation flow
- Recurring schedules use a simplified interval guard (not full cron parsing)

## Security

- Organization isolation on all agents, executions, memory, and workflows
- Tool inputs validated against JSON schemas
- Sensitive tool arguments are not stored in audit logs
- Agents cannot bypass governance on gateway model calls
