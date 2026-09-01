"""Quality platform API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EvaluatorConfig(BaseModel):
    type: str
    name: str
    config: dict = Field(default_factory=dict)
    threshold: float = 0.5
    version: int | None = None


class PipelineCreate(BaseModel):
    name: str
    description: str | None = None
    dataset_id: uuid.UUID
    evaluators: list[dict] = Field(default_factory=list)
    thresholds: dict = Field(default_factory=lambda: {"min_pass_rate": 0.9})
    model: str = "auto"
    parameters: dict = Field(default_factory=dict)
    prompt_version_id: uuid.UUID | None = None
    schedule: str | None = None
    trigger_on: list[str] = Field(default_factory=list)


class PipelineResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    status: str
    dataset_id: uuid.UUID | None
    schedule: str | None
    created_at: datetime


class RunResponse(BaseModel):
    id: uuid.UUID
    pipeline_id: uuid.UUID
    status: str
    pass_count: int
    fail_count: int
    pass_rate: float | None
    total_latency_ms: float
    total_tokens: int
    total_cost: float | None
    trigger: str
    started_at: datetime | None
    completed_at: datetime | None


class RegressionCompareRequest(BaseModel):
    comparison_type: str = "model"
    baseline_label: str
    candidate_label: str
    baseline_run_id: uuid.UUID
    candidate_run_id: uuid.UUID
    thresholds: dict | None = None


class PromptRegressionRequest(BaseModel):
    pipeline_id: uuid.UUID
    baseline_prompt_version_id: uuid.UUID
    candidate_prompt_version_id: uuid.UUID


class GateCreate(BaseModel):
    name: str
    pipeline_id: uuid.UUID
    min_pass_rate: float = 0.9
    min_safety_score: float | None = None
    max_regression_delta: float | None = None
    block_deployment: bool = True


class ProductionConfigUpdate(BaseModel):
    enabled: bool | None = None
    sampling_rate: float | None = None
    sampling_rules: dict | None = None
    redaction_policy: dict | None = None
    retention_days: int | None = None
    pipeline_id: uuid.UUID | None = None


class QualityOverviewResponse(BaseModel):
    pipelines: int
    recent_runs: int
    open_alerts: int
    regressions_detected: int
    overall_quality: float | None
    reliability_score: float | None
    confidence: str | None
    recent_regressions: list[dict] = Field(default_factory=list)
    recent_alerts: list[dict] = Field(default_factory=list)
