from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model import Model
from app.models.request_log import (
    PRICING_SOURCE_MANUAL,
    PRICING_SOURCE_UNKNOWN,
)


class PricingInfo:
    def __init__(
        self,
        input_price_per_million: float,
        output_price_per_million: float,
        currency: str,
        pricing_source: str,
        is_known: bool,
    ) -> None:
        self.input_price_per_million = input_price_per_million
        self.output_price_per_million = output_price_per_million
        self.currency = currency
        self.pricing_source = pricing_source
        self.is_known = is_known


class PricingRegistry:
    """Registry for model pricing used in cost estimation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_pricing(self, model_name: str) -> PricingInfo:
        result = await self.db.execute(
            select(Model).where(Model.provider_model_id == model_name)
        )
        model_record = result.scalar_one_or_none()

        if not model_record:
            return PricingInfo(0.0, 0.0, "USD", PRICING_SOURCE_UNKNOWN, is_known=False)

        input_ppm = model_record.input_price_per_million
        output_ppm = model_record.output_price_per_million

        # Fall back to per-1k fields if per-million not set
        if input_ppm == 0 and model_record.input_price_per_1k > 0:
            input_ppm = model_record.input_price_per_1k * 1000
        if output_ppm == 0 and model_record.output_price_per_1k > 0:
            output_ppm = model_record.output_price_per_1k * 1000

        source = model_record.pricing_source or PRICING_SOURCE_UNKNOWN
        is_known = source not in (PRICING_SOURCE_UNKNOWN,) and (input_ppm > 0 or output_ppm > 0)

        return PricingInfo(
            input_price_per_million=input_ppm,
            output_price_per_million=output_ppm,
            currency=model_record.pricing_currency or "USD",
            pricing_source=source,
            is_known=is_known,
        )

    async def update_pricing(
        self,
        model_id: uuid.UUID,
        input_price_per_million: float,
        output_price_per_million: float,
        pricing_source: str = PRICING_SOURCE_MANUAL,
        currency: str = "USD",
    ) -> Model | None:
        result = await self.db.execute(select(Model).where(Model.id == model_id))
        model_record = result.scalar_one_or_none()
        if not model_record:
            return None

        model_record.input_price_per_million = input_price_per_million
        model_record.output_price_per_million = output_price_per_million
        model_record.input_price_per_1k = input_price_per_million / 1000
        model_record.output_price_per_1k = output_price_per_million / 1000
        model_record.pricing_source = pricing_source
        model_record.pricing_currency = currency
        model_record.pricing_updated_at = datetime.now(UTC)
        await self.db.flush()
        return model_record

    @staticmethod
    def calculate_cost(
        input_tokens: int,
        output_tokens: int,
        pricing: PricingInfo,
    ) -> tuple[float, float, float, bool]:
        if not pricing.is_known:
            return 0.0, 0.0, 0.0, True

        input_cost = (input_tokens / 1_000_000) * pricing.input_price_per_million
        output_cost = (output_tokens / 1_000_000) * pricing.output_price_per_million
        return input_cost, output_cost, input_cost + output_cost, True
