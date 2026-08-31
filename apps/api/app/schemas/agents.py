"""Pydantic schemas for agents and workflows."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str
    description: str | None = None
    system_prompt: str = ""
    model_configuration: dict = Field(default_factory=dict)
    tool_configuration: dict = Field(default_factory=dict)
    memory_configuration: dict = Field(default_factory=dict)
    max_steps: int = 10
    timeout_seconds: int = 300
    max_tokens: int | None = None
    max_budget_usd: float | None = None
    status: str = "draft"


class AgentUpdate(BaseModel):
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
    status: str | None = None


class AgentResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: str | None
    status: str
    system_prompt: str
    model_configuration: dict
    tool_configuration: dict
    memory_configuration: dict
    max_steps: int
    timeout_seconds: int
    max_tokens: int | None
    max_budget_usd: float | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentExecuteRequest(BaseModel):
    input_text: str | None = None
    session_id: str | None = None
    idempotency_key: str | None = None
    sync: bool = False


class AgentStepResponse(BaseModel):
    id: uuid.UUID
    step_number: int
    step_type: str
    model: str | None
    provider: str | None
    tool_name: str | None
    status: str
    latency_ms: float | None
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float | None
    safe_metadata: dict | None = Field(None, validation_alias="metadata")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class AgentExecutionResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    agent_id: uuid.UUID
    status: str
    input_text: str | None
    output_text: str | None
    session_id: str | None
    current_step: int
    total_steps: int
    total_tokens: int
    estimated_cost_usd: float | None
    error_message: str | None
    error_code: str | None
    approval_id: uuid.UUID | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    steps: list[AgentStepResponse] = []

    model_config = {"from_attributes": True}


class AgentOverviewResponse(BaseModel):
    total_agents: int
    active_agents: int
    recent_executions: int
    success_rate: float
    failures: int
    average_duration_ms: float | None
    estimated_cost_usd: float | None


class WorkflowNodeInput(BaseModel):
    node_key: str
    node_type: str
    config: dict = Field(default_factory=dict)
    next_on_success: str | None = None
    next_on_failure: str | None = None
    next_on_true: str | None = None
    next_on_false: str | None = None


class WorkflowCreate(BaseModel):
    name: str
    description: str | None = None
    definition: dict = Field(default_factory=dict)
    nodes: list[WorkflowNodeInput] = Field(default_factory=list)


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    definition: dict | None = None
    nodes: list[WorkflowNodeInput] | None = None
    status: str | None = None


class WorkflowResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: str | None
    status: str
    definition: dict
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    nodes: list[WorkflowNodeInput] = []

    model_config = {"from_attributes": True}


class WorkflowExecuteRequest(BaseModel):
    context: dict = Field(default_factory=dict)
    idempotency_key: str | None = None
    sync: bool = False


class WorkflowExecutionResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    workflow_id: uuid.UUID
    status: str
    current_node_key: str | None
    context: dict
    error_message: str | None
    estimated_cost_usd: float | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkflowScheduleCreate(BaseModel):
    schedule_type: str
    cron_expression: str | None = None
    run_at: datetime | None = None
    is_enabled: bool = True


class WorkflowTriggerCreate(BaseModel):
    trigger_type: str
    secret: str | None = None


class CancelRequest(BaseModel):
    reason: str | None = None
