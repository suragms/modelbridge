# AI Quality & Reliability Platform (Phase 17)

ModelBridge Phase 17 adds an evidence-based quality engineering platform integrated with AI Studio, observability, governance, and the Phase 14 event bus.

## Architecture

```
AI Application
      │
      ▼
Evaluation Input (datasets, regression, production samples)
      │
      ▼
Evaluation Pipeline (versioned evaluators + thresholds)
      │
  ┌───┼───┐
  ▼   ▼   ▼
Rule Regex LLM Judge ...
      │
      ▼
Quality Results → Trends & Scorecards → Alerts & Gates
```

## Evaluator Types

| Type | Methodology |
|------|-------------|
| `rule` | Exact/contains match |
| `regex` | Pattern matching |
| `structured_output` | JSON schema validation |
| `custom` | Organization-defined rules (versioned, audited) |
| `llm_judge` | LLM-generated score — **clearly labeled as subjective** |

LLM judges include: judge model, evaluation prompt, scoring schema, threshold, and limitations in every result.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/quality/overview` | Dashboard summary |
| GET/POST | `/quality/pipelines` | List/create pipelines |
| POST | `/quality/pipelines/{id}/run` | Run pipeline |
| GET | `/quality/regressions` | List regression comparisons |
| POST | `/quality/regressions/compare` | Compare two runs |
| POST | `/quality/regressions/prompt` | Prompt version regression |
| GET | `/quality/scorecards` | List scorecards |
| POST | `/quality/scorecards/reliability` | Compute reliability scorecard |
| GET/POST | `/quality/gates` | Quality gates |
| GET | `/quality/production` | Production sampling status |
| GET | `/quality/models/comparison` | Model quality from runs |

## Quality Gates

Quality gates link to evaluation pipelines and can **block deployments** when pass rate falls below threshold. Integrated into Studio deployment validation (`DeploymentService.validate`).

## Production Sampling

- Configurable sampling rate and retention
- Request metadata only (no prompt content stored)
- Hashed request IDs
- Redaction policy applied

## Events

- `evaluation.completed` / `evaluation.failed`
- `quality.regression.detected`
- `quality.threshold.violated`
- `quality.gate.failed`

## CLI

```bash
modelbridge quality overview --json
modelbridge quality pipelines --json
modelbridge quality run <pipeline-id> --json
modelbridge quality regressions --json
```

## Metrics

- `modelbridge_quality_evaluations_total`
- `modelbridge_quality_regressions_total`
- `modelbridge_quality_gate_failures_total`
- `modelbridge_quality_alerts_total`

## Limitations

- **LLM judges** produce subjective scores, not objective truth
- **Bias testing** compares group scores but does not prove fairness
- **Hallucination checks** use heuristics (reference overlap) with documented limits
- **Production sampling** uses request metadata only — full output evaluation requires dataset-based pipelines
- **Scorecards** require sufficient sample counts; low confidence when data is sparse

## Security

- Organization isolation on all quality resources
- Production samples org-scoped with hashed IDs
- Cross-tenant access returns 404
- Quality gate bypass prevented at deployment approve step
