"""Agent memory abstraction (database-backed)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentMemory, MemoryScope


class MemoryStore:
    def __init__(self, db: AsyncSession, organization_id: uuid.UUID, agent_id: uuid.UUID):
        self.db = db
        self.organization_id = organization_id
        self.agent_id = agent_id

    async def get(
        self,
        key: str,
        *,
        scope: str,
        session_id: str | None = None,
        execution_id: uuid.UUID | None = None,
    ) -> dict | None:
        filters = [
            AgentMemory.organization_id == self.organization_id,
            AgentMemory.agent_id == self.agent_id,
            AgentMemory.scope == scope,
            AgentMemory.key == key,
        ]
        if scope == MemoryScope.SESSION and session_id:
            filters.append(AgentMemory.session_id == session_id)
        if scope == MemoryScope.EXECUTION and execution_id:
            filters.append(AgentMemory.execution_id == execution_id)
        result = await self.db.execute(select(AgentMemory).where(and_(*filters)).limit(1))
        row = result.scalar_one_or_none()
        if not row:
            return None
        if row.expires_at and row.expires_at < datetime.now(UTC):
            return None
        return row.value

    async def set(
        self,
        key: str,
        value: dict,
        *,
        scope: str,
        session_id: str | None = None,
        execution_id: uuid.UUID | None = None,
        ttl_hours: int | None = None,
    ) -> None:
        expires = None
        if ttl_hours:
            expires = datetime.now(UTC) + timedelta(hours=ttl_hours)
        row = AgentMemory(
            organization_id=self.organization_id,
            agent_id=self.agent_id,
            scope=scope,
            session_id=session_id,
            execution_id=execution_id,
            key=key,
            value=value,
            expires_at=expires,
        )
        self.db.add(row)
        await self.db.flush()

    async def clear_agent_memory(self) -> int:
        result = await self.db.execute(
            delete(AgentMemory).where(
                AgentMemory.organization_id == self.organization_id,
                AgentMemory.agent_id == self.agent_id,
                AgentMemory.scope == MemoryScope.AGENT,
            )
        )
        return result.rowcount or 0
