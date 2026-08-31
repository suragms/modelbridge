"""ARQ tasks for agent and workflow execution."""

from __future__ import annotations

import uuid

import structlog

from app.db.base import async_session_factory
from app.services.agents.engine import AgentExecutionEngine
from app.services.agents.workflow_engine import WorkflowExecutionEngine

logger = structlog.get_logger()


async def execute_agent_job(ctx, execution_id: str) -> dict:
    del ctx
    async with async_session_factory() as db:
        engine = AgentExecutionEngine(db)
        execution = await engine.run(uuid.UUID(execution_id))
        return {"execution_id": str(execution.id), "status": execution.status}


async def execute_workflow_job(ctx, execution_id: str) -> dict:
    del ctx
    async with async_session_factory() as db:
        engine = WorkflowExecutionEngine(db)
        execution = await engine.run(uuid.UUID(execution_id))
        return {"execution_id": str(execution.id), "status": execution.status}


async def run_scheduled_workflows(ctx) -> dict:
    """Check one-time and recurring workflow schedules."""
    del ctx
    from datetime import UTC, datetime

    from sqlalchemy import select

    from app.models.agent import WorkflowSchedule, WorkflowStatus, Workflow
    from app.models.agent import WorkflowExecution
    from app.services.agents.queue import enqueue_workflow_execution

    triggered = 0
    async with async_session_factory() as db:
        now = datetime.now(UTC)
        result = await db.execute(
            select(WorkflowSchedule, Workflow)
            .join(Workflow, Workflow.id == WorkflowSchedule.workflow_id)
            .where(
                WorkflowSchedule.is_enabled == True,  # noqa: E712
                Workflow.status == WorkflowStatus.ACTIVE,
            )
        )
        for schedule, workflow in result.all():
            should_run = False
            if schedule.schedule_type == "one_time" and schedule.run_at and schedule.run_at <= now:
                if not schedule.last_run_at:
                    should_run = True
            elif schedule.schedule_type == "recurring" and schedule.cron_expression:
                # Simple hourly/daily guard using last_run_at
                if not schedule.last_run_at or (now - schedule.last_run_at).total_seconds() >= 3600:
                    should_run = True
            if not should_run:
                continue
            wf_exec = WorkflowExecution(
                organization_id=schedule.organization_id,
                workflow_id=workflow.id,
                status="queued",
            )
            db.add(wf_exec)
            schedule.last_run_at = now
            await db.flush()
            await enqueue_workflow_execution(str(wf_exec.id))
            triggered += 1
        await db.commit()
    return {"triggered": triggered}
