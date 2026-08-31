"""Automation triggers and execution."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform import Automation, AutomationExecution, AutomationExecutionStatus, AutomationStatus

INTEGRATION_TEMPLATES = [
    {
        "id": "provider_health_alert",
        "name": "Provider Health Alert",
        "description": "Trigger on provider.degraded events",
        "trigger_type": "event",
        "trigger_config": {"event_type": "provider.degraded"},
        "action_type": "webhook",
    },
    {
        "id": "deployment_notification",
        "name": "Deployment Notification",
        "description": "Notify on deployment.completed",
        "trigger_type": "event",
        "trigger_config": {"event_type": "deployment.completed"},
        "action_type": "webhook",
    },
    {
        "id": "cost_alert",
        "name": "Cost Alert",
        "description": "Trigger workflow on anomaly.detected",
        "trigger_type": "event",
        "trigger_config": {"event_type": "anomaly.detected"},
        "action_type": "start_workflow",
    },
    {
        "id": "github_deploy_trigger",
        "name": "GitHub Deployment Trigger",
        "description": "Start workflow on push events from GitHub",
        "trigger_type": "github_event",
        "trigger_config": {"event": "push"},
        "action_type": "start_workflow",
    },
]


class AutomationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def list_templates() -> list[dict]:
        return INTEGRATION_TEMPLATES

    async def create(
        self,
        *,
        organization_id: uuid.UUID,
        name: str,
        trigger_type: str,
        trigger_config: dict,
        action_type: str,
        action_config: dict,
        description: str | None = None,
        template_id: str | None = None,
        requires_approval: bool = False,
        created_by: uuid.UUID | None,
    ) -> Automation:
        automation = Automation(
            organization_id=organization_id,
            name=name,
            description=description,
            trigger_type=trigger_type,
            trigger_config=trigger_config,
            action_type=action_type,
            action_config=action_config,
            template_id=template_id,
            requires_approval=requires_approval or action_type in {"start_workflow", "send_webhook"},
            status=AutomationStatus.ACTIVE,
            created_by=created_by,
        )
        self.db.add(automation)
        await self.db.flush()
        return automation

    async def list_automations(self, organization_id: uuid.UUID) -> list[Automation]:
        result = await self.db.execute(
            select(Automation)
            .where(Automation.organization_id == organization_id)
            .order_by(Automation.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, organization_id: uuid.UUID, automation_id: uuid.UUID) -> Automation | None:
        a = await self.db.get(Automation, automation_id)
        if not a or a.organization_id != organization_id:
            return None
        return a

    async def execute(
        self,
        automation: Automation,
        *,
        event_id: uuid.UUID | None = None,
        context: dict | None = None,
        force: bool = False,
    ) -> AutomationExecution:
        if automation.requires_approval and not force:
            execution = AutomationExecution(
                organization_id=automation.organization_id,
                automation_id=automation.id,
                event_id=event_id,
                status=AutomationExecutionStatus.SKIPPED,
                trigger_summary="Approval required",
                result_summary={"reason": "requires_approval"},
            )
            self.db.add(execution)
            await self.db.flush()
            return execution

        execution = AutomationExecution(
            organization_id=automation.organization_id,
            automation_id=automation.id,
            event_id=event_id,
            status=AutomationExecutionStatus.RUNNING,
            trigger_summary=str(automation.trigger_config),
            started_at=datetime.now(UTC),
        )
        self.db.add(execution)
        await self.db.flush()

        try:
            result = await self._run_action(automation, context or {})
            execution.status = AutomationExecutionStatus.COMPLETED
            execution.result_summary = result
            execution.completed_at = datetime.now(UTC)
        except Exception as e:
            execution.status = AutomationExecutionStatus.FAILED
            execution.error_message = str(e)[:500]
            execution.completed_at = datetime.now(UTC)

        await self.db.flush()
        return execution

    async def _run_action(self, automation: Automation, context: dict) -> dict:
        action = automation.action_type
        cfg = automation.action_config or {}

        if action == "start_workflow":
            workflow_id = cfg.get("workflow_id")
            if not workflow_id:
                raise ValueError("workflow_id required")
            from app.models.agent import WorkflowExecution, WorkflowStatus, Workflow
            from app.services.agents.workflow_engine import WORKFLOW_QUEUED

            wf = await self.db.get(Workflow, uuid.UUID(str(workflow_id)))
            if not wf or wf.organization_id != automation.organization_id:
                raise ValueError("Workflow not found")
            if wf.status != WorkflowStatus.ACTIVE:
                raise ValueError("Workflow is not active")

            execution = WorkflowExecution(
                organization_id=automation.organization_id,
                workflow_id=wf.id,
                status=WORKFLOW_QUEUED,
                context=context,
            )
            self.db.add(execution)
            await self.db.flush()

            try:
                from app.services.agents.queue import enqueue_workflow_execution

                await enqueue_workflow_execution(execution.id)
            except Exception:
                from app.services.agents.workflow_engine import WorkflowExecutionEngine

                await WorkflowExecutionEngine(self.db).run(execution.id)

            return {"workflow_execution_id": str(execution.id)}

        if action == "send_webhook":
            webhook_id = cfg.get("webhook_id")
            if not webhook_id:
                raise ValueError("webhook_id required")
            return {"webhook_id": str(webhook_id), "queued": True}

        if action == "create_notification":
            return {"notification": cfg.get("message", "Automation triggered")}

        if action == "generate_recommendation":
            return {"note": "Recommendation generation delegated to intelligence layer"}

        raise ValueError(f"Unknown action type: {action}")

    async def list_executions(
        self, organization_id: uuid.UUID, automation_id: uuid.UUID | None = None, limit: int = 50
    ) -> list[AutomationExecution]:
        q = select(AutomationExecution).where(
            AutomationExecution.organization_id == organization_id
        ).order_by(AutomationExecution.created_at.desc()).limit(limit)
        if automation_id:
            q = q.where(AutomationExecution.automation_id == automation_id)
        result = await self.db.execute(q)
        return list(result.scalars().all())
