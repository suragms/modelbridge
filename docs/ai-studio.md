# AI Studio (Phase 16)

ModelBridge AI Studio is a visual development environment for building, testing, evaluating, and deploying AI systems. Every Studio feature connects to real backend services — workflows compile to the Phase 9 execution engine, prompts and playground calls use the gateway, and automations reuse the Phase 14 automation platform.

## Architecture

```
Visual Builder
      │
      ├── Workflow Builder  → StudioWorkflowVersion → compile → WorkflowNode
      ├── Agent Builder     → Agent + StudioAgentVersion
      ├── Prompt Studio     → PromptTemplate + PromptVersion
      ├── Evaluation Studio → EvaluationSuite + EvaluationRun
      └── Deployment Builder → StudioDeployment pipeline
              │
              ▼
      Validation & Governance (RBAC, org isolation)
              │
              ▼
         Execution Engine / Gateway
```

## Dashboard

- **Studio home**: `/studio` — counts and recent version history
- **Workflows**: `/studio/workflows` — drag-and-drop canvas, publish to engine
- **Agents**: `/studio/agents` — view and configure organization agents
- **Prompts**: `/studio/prompts` — templates, versioning, quick test
- **Playground**: `/studio/playground` — model comparison via real pipeline
- **Evaluations**: `/studio/evaluations` and `/studio/evaluations/datasets`
- **Automations**: `/studio/automations` — Phase 14 automations in Studio context
- **Deployments**: `/studio/deployments` — draft → validate → approve → deploy

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/studio/overview` | Studio dashboard counts |
| GET | `/studio/nodes` | Node type catalog and schemas |
| GET/POST | `/studio/workflows` | List/create visual workflows |
| POST | `/studio/workflows/{id}/publish` | Validate and compile to engine |
| GET/PATCH | `/studio/agents` | List/update agents |
| POST | `/studio/compare` | Multi-model comparison |
| GET/POST | `/studio/deployments` | Deployment pipelines |
| GET/POST | `/prompts/` | Prompt templates |
| POST | `/prompts/{id}/versions` | Immutable prompt versions |
| POST | `/prompts/{id}/test` | Test via gateway |
| GET/POST | `/evaluations/datasets` | Evaluation datasets |
| GET/POST | `/evaluations/` | Evaluation suites |
| POST | `/evaluations/{id}/run` | Run evaluation suite |
| GET | `/evaluation-runs/{id}` | Evaluation run status |

All endpoints enforce organization isolation and RBAC (`studio.read`, `studio.manage`, `prompts.manage`, `evaluations.manage`).

## Workflow Nodes

Supported node types: `trigger`, `ai_model`, `agent`, `condition`, `transform`, `integration`, `webhook`, `approval`, `output`.

Validation checks:
- Compatible connections
- Required configuration (e.g. `agent_id`, `model`)
- Cycle detection
- Engine-level validation via existing workflow validator

## Prompt Variables

Use `{{variable_name}}` placeholders. Variables are validated; secret-like names (`api_key`, `password`, etc.) are never substituted.

## Evaluation Scorers

Objective scorers (implemented):
- `exact_match`
- `contains`
- `regex`
- `json_schema`

## CLI

```bash
modelbridge studio overview --json
modelbridge studio workflows list --json
modelbridge prompts list --json
modelbridge prompts test <prompt-id> --input "Hello"
modelbridge evaluations datasets --json
modelbridge evaluations run <suite-id> --json
```

## SDK

**Python**

```python
from modelbridge import ModelBridge

client = ModelBridge(token="...", org_id="...")
client.studio.overview()
client.prompts.list()
client.prompts.test(prompt_id, input="Hello")
client.evaluations.run(suite_id)
```

**TypeScript**

```typescript
await mb.studio.listWorkflows();
await mb.prompts.test(promptId, { input: "Hello" });
await mb.evaluations.run(suiteId);
```

## Import / Export

Export uses format `modelbridge-studio-v1` with secrets stripped. Import validates format and rejects payloads containing secret patterns.

## Metrics

Prometheus counters:
- `modelbridge_studio_workflows_total`
- `modelbridge_prompt_executions_total`
- `modelbridge_evaluation_runs_total`
- `modelbridge_studio_deployments_total`

## Security

- Cross-tenant access returns 404
- Tool attachment validates against builtin tool registry and RBAC
- Agent safety limits capped server-side (`max_steps` ≤ 50, `timeout_seconds` ≤ 600)
- Deployment approval requires `governance.approve` permission
- Secrets never exported in import/export payloads

## Known Limitations

- Workflow canvas draft updates require re-create or publish from current draft version
- Import endpoint validates but does not yet materialize resources automatically
- AI-based semantic scorers are not implemented (objective scorers only)
- Integration nodes compile to tool stubs — verify integrations are configured separately

## Marketplace Templates

Install workflow, agent, prompt, and automation templates from `/marketplace` using existing marketplace controls.
