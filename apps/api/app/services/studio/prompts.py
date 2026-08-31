"""Prompt template management and testing."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.studio import PromptTemplate, PromptVersion, StudioVersionHistory
from app.schemas.chat import ChatCompletionRequest, ChatMessage
from app.services.gateway import execute_chat
from app.services.metrics import record_prompt_execution
from app.services.studio.workflows import substitute_prompt_variables

VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def extract_variables(content: str) -> list[dict]:
    names = sorted(set(VARIABLE_PATTERN.findall(content)))
    return [{"name": n, "type": "string", "required": True} for n in names]


def validate_variables(variables: list[dict]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for var in variables:
        name = var.get("name")
        if not name:
            errors.append("Variable missing name")
            continue
        if name in seen:
            errors.append(f"Duplicate variable: {name}")
        seen.add(name)
        if var.get("type") not in {None, "string", "number", "boolean"}:
            errors.append(f"Invalid type for {name}")
    return errors


class PromptService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        org_id: uuid.UUID,
        name: str,
        content: str,
        description: str | None = None,
        tags: list[str] | None = None,
        variables: list[dict] | None = None,
        change_notes: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> tuple[PromptTemplate, PromptVersion]:
        inferred = variables if variables is not None else extract_variables(content)
        var_errors = validate_variables(inferred)
        if var_errors:
            raise ValueError("; ".join(var_errors))

        prompt = PromptTemplate(
            organization_id=org_id,
            name=name,
            description=description,
            tags=tags or [],
            owner_id=user_id,
        )
        self.db.add(prompt)
        await self.db.flush()

        version = PromptVersion(
            prompt_id=prompt.id,
            version=1,
            content=content,
            variables=inferred,
            change_notes=change_notes or "Initial version",
            created_by=user_id,
        )
        self.db.add(version)
        await self.db.flush()

        prompt.current_version_id = version.id
        self._history(org_id, "prompt", prompt.id, 1, user_id, "Created")
        await self.db.flush()
        return prompt, version

    async def add_version(
        self,
        prompt: PromptTemplate,
        *,
        content: str,
        variables: list[dict] | None = None,
        change_notes: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> PromptVersion:
        result = await self.db.execute(
            select(func.max(PromptVersion.version)).where(PromptVersion.prompt_id == prompt.id)
        )
        max_ver = result.scalar() or 0
        inferred = variables if variables is not None else extract_variables(content)
        var_errors = validate_variables(inferred)
        if var_errors:
            raise ValueError("; ".join(var_errors))

        version = PromptVersion(
            prompt_id=prompt.id,
            version=max_ver + 1,
            content=content,
            variables=inferred,
            change_notes=change_notes,
            created_by=user_id,
        )
        self.db.add(version)
        await self.db.flush()
        prompt.current_version_id = version.id
        prompt.updated_at = datetime.now(UTC)
        self._history(prompt.organization_id, "prompt", prompt.id, version.version, user_id, change_notes)
        await self.db.flush()
        return version

    async def list_prompts(self, org_id: uuid.UUID) -> list[PromptTemplate]:
        result = await self.db.execute(
            select(PromptTemplate)
            .where(PromptTemplate.organization_id == org_id)
            .order_by(PromptTemplate.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, org_id: uuid.UUID, prompt_id: uuid.UUID) -> PromptTemplate | None:
        p = await self.db.get(PromptTemplate, prompt_id)
        if not p or p.organization_id != org_id:
            return None
        return p

    async def list_versions(self, prompt_id: uuid.UUID) -> list[PromptVersion]:
        result = await self.db.execute(
            select(PromptVersion)
            .where(PromptVersion.prompt_id == prompt_id)
            .order_by(PromptVersion.version.desc())
        )
        return list(result.scalars().all())

    async def test_prompt(
        self,
        version: PromptVersion,
        *,
        user,
        db: AsyncSession,
        input_text: str,
        variables: dict | None = None,
        model: str = "auto",
        parameters: dict | None = None,
    ) -> dict:
        content, errors = substitute_prompt_variables(version.content, variables or {})
        if errors:
            raise ValueError("; ".join(errors))

        messages = [ChatMessage(role="user", content=input_text)]
        if content:
            messages.insert(0, ChatMessage(role="system", content=content))

        params = parameters or {}
        result = await execute_chat(
            ChatCompletionRequest(
                model=model,
                messages=messages,
                temperature=params.get("temperature"),
                max_tokens=params.get("max_tokens"),
            ),
            db,
            user,
            None,
        )
        record_prompt_execution(status="completed")
        output = ""
        if result.response.choices:
            output = result.response.choices[0].message.content or ""
        return {
            "output": output,
            "latency_ms": result.latency_ms,
            "estimated_cost": result.estimated_total_cost,
            "cost_type": "estimated",
            "usage_source": result.usage_source,
            "model": result.selected_model,
            "provider": result.provider,
        }

    def _history(
        self,
        org_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
        version: int,
        actor_id: uuid.UUID | None,
        summary: str | None,
    ) -> None:
        self.db.add(
            StudioVersionHistory(
                organization_id=org_id,
                resource_type=resource_type,
                resource_id=resource_id,
                version=version,
                actor_id=actor_id,
                change_summary=summary,
            )
        )
