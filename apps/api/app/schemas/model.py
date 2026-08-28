from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ModelResponse(BaseModel):
    id: uuid.UUID
    provider_model_id: str
    display_name: str
    context_window: int
    max_output_tokens: int | None = None
    embedding_dimensions: int | None = None
    input_price_per_1k: float
    output_price_per_1k: float
    supports_chat: bool = True
    supports_streaming: bool
    supports_tools: bool
    supports_tool_choice: bool = False
    supports_embeddings: bool
    supports_vision: bool
    supports_json_mode: bool
    supports_structured_output: bool = False
    supports_reasoning: bool = False
    is_enabled: bool
    quality_score: float
    provider_id: uuid.UUID
    average_latency_ms: float | None = None
    last_synced_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ModelUpdate(BaseModel):
    display_name: str | None = None
    is_enabled: bool | None = None
    quality_score: float | None = None
    input_price_per_1k: float | None = None
    output_price_per_1k: float | None = None
    max_output_tokens: int | None = None
    embedding_dimensions: int | None = None
