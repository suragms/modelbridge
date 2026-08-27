from __future__ import annotations

import uuid

from pydantic import BaseModel


class ModelResponse(BaseModel):
    id: uuid.UUID
    provider_model_id: str
    display_name: str
    context_window: int
    input_price_per_1k: float
    output_price_per_1k: float
    supports_streaming: bool
    supports_tools: bool
    supports_embeddings: bool
    supports_vision: bool
    supports_json_mode: bool
    is_enabled: bool
    quality_score: float
    provider_id: uuid.UUID

    model_config = {"from_attributes": True}


class ModelUpdate(BaseModel):
    display_name: str | None = None
    is_enabled: bool | None = None
    quality_score: float | None = None
    input_price_per_1k: float | None = None
    output_price_per_1k: float | None = None
