"""AI Studio API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class StudioOverviewResponse(BaseModel):
    workflows: int
    agents: int
    prompts: int
    evaluations: int
    deployments: int
    recent_activity: list[dict] = Field(default_factory=list)


class PromptCreate(BaseModel):
    name: str
    content: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    variables: list[dict] = Field(default_factory=list)
    change_notes: str | None = None


class PromptVersionCreate(BaseModel):
    content: str
    variables: list[dict] | None = None
    change_notes: str | None = None


class PromptTestRequest(BaseModel):
    input: str
    variables: dict = Field(default_factory=dict)
    model: str = "auto"
    parameters: dict = Field(default_factory=dict)


class PromptResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    tags: list[str]
    current_version_id: uuid.UUID | None
    usage_count: int
    created_at: datetime
    updated_at: datetime


class PromptVersionResponse(BaseModel):
    id: uuid.UUID
    version: int
    content: str
    variables: list[dict]
    change_notes: str | None
    created_at: datetime
    created_by: uuid.UUID | None = None


class DatasetCreate(BaseModel):
    name: str
    description: str | None = None
    test_cases: list[dict] = Field(default_factory=list)


class DatasetResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    version: int
    test_case_count: int
    created_at: datetime


class EvaluationSuiteCreate(BaseModel):
    name: str
    dataset_id: uuid.UUID
    description: str | None = None
    prompt_version_id: uuid.UUID | None = None
    model: str = "auto"
    parameters: dict = Field(default_factory=dict)
    scorers: list[dict] = Field(default_factory=lambda: [{"type": "exact_match"}])


class EvaluationRunResponse(BaseModel):
    id: uuid.UUID
    suite_id: uuid.UUID
    status: str
    pass_count: int
    fail_count: int
    total_latency_ms: float
    total_tokens: int
    pass_rate: float | None = None
    started_at: datetime | None
    completed_at: datetime | None


class EvaluationResultResponse(BaseModel):
    case_index: int
    input_text: str
    expected: str | None
    actual_output: str | None
    passed: bool
    scorer: str
    score_detail: str | None
    latency_ms: float | None


class StudioWorkflowCreate(BaseModel):
    name: str
    description: str | None = None
    visual_definition: dict = Field(default_factory=dict)


class StudioWorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    visual_definition: dict | None = None
    change_summary: str | None = None


class StudioWorkflowVersionResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    version: int
    status: str
    visual_definition: dict
    change_summary: str | None
    created_at: datetime


class StudioAgentConfigUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    model_configuration: dict | None = None
    tool_configuration: dict | None = None
    memory_configuration: dict | None = None
    max_steps: int | None = None
    timeout_seconds: int | None = None
    max_tokens: int | None = None
    max_budget_usd: float | None = None
    prompt_version_id: uuid.UUID | None = None


class StudioDeploymentCreate(BaseModel):
    name: str
    resource_type: str
    resource_id: uuid.UUID
    version_id: uuid.UUID | None = None
    environment_id: uuid.UUID | None = None


class StudioCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class StudioCompareRequest(BaseModel):
    models: list[str] = Field(min_length=2, max_length=4)
    messages: list[dict]
    temperature: float | None = None
    max_tokens: int | None = None
    prompt_version_id: uuid.UUID | None = None
    variables: dict = Field(default_factory=dict)


class ImportRequest(BaseModel):
    payload: dict
