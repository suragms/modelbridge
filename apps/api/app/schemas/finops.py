"""FinOps API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class FinopsOverviewResponse(BaseModel):
    current_spend: float
    cost_type: str
    request_count: int
    period: str
    top_cost_drivers: list[dict] = Field(default_factory=list)
    open_anomalies: int = 0
    active_budgets: int = 0
    forecast_amount: float | None = None
    optimization_count: int = 0


class BudgetCreate(BaseModel):
    name: str
    amount: float
    scope: str = "organization"
    scope_id: uuid.UUID | None = None
    currency: str = "USD"
    period: str = "monthly"
    thresholds: list[int] = Field(default_factory=lambda: [50, 75, 90, 100])
    enforcement_action: str = "alert"


class BudgetResponse(BaseModel):
    id: uuid.UUID
    name: str
    scope: str
    amount: float
    currency: str
    period: str
    enabled: bool
    created_at: datetime


class PricingVersionCreate(BaseModel):
    provider: str
    model: str
    input_price_per_million: float
    output_price_per_million: float
    currency: str = "USD"


class CostExploreParams(BaseModel):
    days: int = 30
    provider: str | None = None
    model: str | None = None
    breakdown: str = "provider"
