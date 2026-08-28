from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_api_key_or_user
from app.db.base import get_db
from app.models.api_key import APIKey
from app.models.user import User
from app.schemas.chat import EmbeddingRequest, EmbeddingResponse
from app.services.gateway import auth_context, execute_embeddings
from app.services.gateway_guard import enforce_gateway_guards

router = APIRouter(tags=["OpenAI-Compatible"])


@router.post("/v1/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(
    payload: EmbeddingRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    principal: tuple[User | None, APIKey | None] = Depends(get_api_key_or_user),
):
    """OpenAI-compatible embeddings endpoint with capability-aware routing."""
    user, api_key = principal
    _, _, org_id = auth_context(user, api_key)

    inputs = payload.input if isinstance(payload.input, list) else [payload.input]
    combined = "\n".join(str(i) for i in inputs)
    rate_headers = await enforce_gateway_guards(
        request,
        db,
        user=user,
        api_key=api_key,
        organization_id=org_id,
        path="/v1/embeddings",
        input_text=combined,
    )
    request.state.rate_limit_headers = rate_headers
    return await execute_embeddings(payload, db, user, api_key)
