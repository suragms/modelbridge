from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user
from app.db.base import get_db
from app.models.model import Model
from app.models.user import User
from app.schemas.model import ModelResponse, ModelUpdate

router = APIRouter(prefix="/models", tags=["Models"])


@router.get("/", response_model=list[ModelResponse])
async def list_models(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Model).order_by(Model.display_name))
    models = result.scalars().all()
    return [ModelResponse.model_validate(m) for m in models]


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Model).where(Model.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return ModelResponse.model_validate(model)


@router.put("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: uuid.UUID,
    payload: ModelUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Model).where(Model.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if payload.display_name is not None:
        model.display_name = payload.display_name
    if payload.is_enabled is not None:
        model.is_enabled = payload.is_enabled
    if payload.quality_score is not None:
        model.quality_score = payload.quality_score
    if payload.input_price_per_1k is not None:
        model.input_price_per_1k = payload.input_price_per_1k
    if payload.output_price_per_1k is not None:
        model.output_price_per_1k = payload.output_price_per_1k

    await db.flush()
    return ModelResponse.model_validate(model)
