"""Developer platform APIs: events, webhooks, integrations, automations."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.encryption import decrypt_secret
from app.auth.org_context import OrgContext
from app.auth.rbac import Permission, require_permission
from app.db.base import get_db
from app.schemas.platform import (
    AutomationCreate,
    AutomationExecuteRequest,
    AutomationExecutionResponse,
    AutomationResponse,
    AutomationTemplateResponse,
    AutomationUpdate,
    DeveloperActivityEntry,
    EventCatalogEntry,
    IntegrationConnect,
    IntegrationCreate,
    IntegrationResponse,
    IntegrationUpdate,
    PlatformEventResponse,
    WebhookCreate,
    WebhookCreated,
    WebhookDeliveryResponse,
    WebhookResponse,
    WebhookUpdate,
)
from app.services.enterprise.activity import record_activity
from app.services.platform.automations import AutomationService
from app.services.platform.delivery import DeliveryService
from app.services.platform.events import EventBus, EventCatalog
from app.services.platform.integrations import IntegrationService
from app.services.platform.ssrf import SSRFError
from app.services.platform.webhooks import WebhookService

events_router = APIRouter(prefix="/events", tags=["Events"])
webhooks_router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
integrations_router = APIRouter(prefix="/integrations", tags=["Integrations"])
automations_router = APIRouter(prefix="/automations", tags=["Automations"])
developer_router = APIRouter(prefix="/developer", tags=["Developer Portal"])


def _event_response(event, bus: EventBus) -> PlatformEventResponse:
    envelope = bus.envelope(event)
    return PlatformEventResponse(
        id=event.id,
        type=event.event_type,
        organization_id=event.organization_id,
        timestamp=event.created_at,
        schema_version=event.schema_version,
        data=envelope["data"],
        source=event.source,
    )


@events_router.get("/catalog", response_model=list[EventCatalogEntry])
async def event_catalog(
    ctx: OrgContext = Depends(require_permission(Permission.EVENTS_READ)),
):
    return [EventCatalogEntry(**e) for e in EventCatalog.list_events()]


@events_router.get("/", response_model=list[PlatformEventResponse])
async def list_events(
    event_type: str | None = None,
    limit: int = 50,
    ctx: OrgContext = Depends(require_permission(Permission.EVENTS_READ)),
    db: AsyncSession = Depends(get_db),
):
    bus = EventBus(db)
    events = await bus.list_events(ctx.organization_id, event_type=event_type, limit=min(limit, 100))
    return [_event_response(e, bus) for e in events]


@events_router.get("/{event_id}", response_model=PlatformEventResponse)
async def get_event(
    event_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.EVENTS_READ)),
    db: AsyncSession = Depends(get_db),
):
    bus = EventBus(db)
    event = await bus.get_event(ctx.organization_id, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return _event_response(event, bus)


def _webhook_response(wh) -> WebhookResponse:
    return WebhookResponse(
        id=wh.id,
        name=wh.name,
        url=wh.url,
        event_types=wh.event_types or [],
        status=wh.status,
        secret_prefix=wh.secret_prefix,
        created_at=wh.created_at,
        updated_at=wh.updated_at,
    )


@webhooks_router.get("/", response_model=list[WebhookResponse])
async def list_webhooks(
    ctx: OrgContext = Depends(require_permission(Permission.WEBHOOKS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    items = await WebhookService(db).list_endpoints(ctx.organization_id)
    return [_webhook_response(w) for w in items]


@webhooks_router.post("/", response_model=WebhookCreated, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    payload: WebhookCreate,
    ctx: OrgContext = Depends(require_permission(Permission.WEBHOOKS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    try:
        endpoint, secret = await WebhookService(db).create(
            organization_id=ctx.organization_id,
            name=payload.name,
            url=payload.url,
            event_types=payload.event_types,
            created_by=ctx.user.id,
        )
    except SSRFError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    await record_activity(
        db,
        organization_id=ctx.organization_id,
        event_type="webhook.created",
        resource_type="webhook",
        resource_id=str(endpoint.id),
        actor_id=ctx.user.id,
        metadata={"name": payload.name},
    )
    await db.commit()
    resp = _webhook_response(endpoint)
    return WebhookCreated(**resp.model_dump(), secret=secret)


@webhooks_router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.WEBHOOKS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    wh = await WebhookService(db).get(ctx.organization_id, webhook_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return _webhook_response(wh)


@webhooks_router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: uuid.UUID,
    payload: WebhookUpdate,
    ctx: OrgContext = Depends(require_permission(Permission.WEBHOOKS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    svc = WebhookService(db)
    wh = await svc.get(ctx.organization_id, webhook_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    try:
        wh = await svc.update(
            wh,
            name=payload.name,
            url=payload.url,
            event_types=payload.event_types,
            status=payload.status,
        )
    except SSRFError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await db.commit()
    return _webhook_response(wh)


@webhooks_router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.WEBHOOKS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    svc = WebhookService(db)
    wh = await svc.get(ctx.organization_id, webhook_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await svc.delete(wh)
    await db.commit()


@webhooks_router.post("/{webhook_id}/rotate-secret", response_model=WebhookCreated)
async def rotate_webhook_secret(
    webhook_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.WEBHOOKS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    svc = WebhookService(db)
    wh = await svc.get(ctx.organization_id, webhook_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    secret = await svc.rotate_secret(wh)
    await db.commit()
    resp = _webhook_response(wh)
    return WebhookCreated(**resp.model_dump(), secret=secret)


@webhooks_router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse])
async def list_deliveries(
    webhook_id: uuid.UUID,
    limit: int = 50,
    ctx: OrgContext = Depends(require_permission(Permission.WEBHOOKS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    wh = await WebhookService(db).get(ctx.organization_id, webhook_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    deliveries = await WebhookService(db).list_deliveries(
        ctx.organization_id, webhook_id, limit=min(limit, 100)
    )
    return [
        WebhookDeliveryResponse(
            id=d.id,
            webhook_id=d.webhook_id,
            event_id=d.event_id,
            status=d.status,
            attempt_count=d.attempt_count,
            max_attempts=d.max_attempts,
            last_attempt_at=d.last_attempt_at,
            next_retry_at=d.next_retry_at,
            response_status=d.response_status,
            failure_category=d.failure_category,
            created_at=d.created_at,
            completed_at=d.completed_at,
        )
        for d in deliveries
    ]


@webhooks_router.post("/{webhook_id}/deliveries/{delivery_id}/retry", response_model=WebhookDeliveryResponse)
async def retry_delivery(
    webhook_id: uuid.UUID,
    delivery_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.WEBHOOKS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    wh = await WebhookService(db).get(ctx.organization_id, webhook_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    try:
        delivery = await DeliveryService(db).manual_retry(ctx.organization_id, delivery_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    if delivery.webhook_id != webhook_id:
        raise HTTPException(status_code=404, detail="Delivery not found")
    await db.commit()
    return WebhookDeliveryResponse(
        id=delivery.id,
        webhook_id=delivery.webhook_id,
        event_id=delivery.event_id,
        status=delivery.status,
        attempt_count=delivery.attempt_count,
        max_attempts=delivery.max_attempts,
        last_attempt_at=delivery.last_attempt_at,
        next_retry_at=delivery.next_retry_at,
        response_status=delivery.response_status,
        failure_category=delivery.failure_category,
        created_at=delivery.created_at,
        completed_at=delivery.completed_at,
    )


def _integration_response(i) -> IntegrationResponse:
    safe_config = {k: v for k, v in (i.config or {}).items() if k not in {"webhook_secret_encrypted"}}
    return IntegrationResponse(
        id=i.id,
        provider=i.provider,
        name=i.name,
        status=i.status,
        config=safe_config,
        last_sync_at=i.last_sync_at,
        last_error=i.last_error,
        created_at=i.created_at,
        updated_at=i.updated_at,
    )


@integrations_router.get("/", response_model=list[IntegrationResponse])
async def list_integrations(
    ctx: OrgContext = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    items = await IntegrationService(db).list_integrations(ctx.organization_id)
    return [_integration_response(i) for i in items]


@integrations_router.post("/", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_integration(
    payload: IntegrationCreate,
    ctx: OrgContext = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    integration = await IntegrationService(db).create(
        organization_id=ctx.organization_id,
        provider=payload.provider,
        name=payload.name,
        config=payload.config,
        created_by=ctx.user.id,
    )
    await db.commit()
    return _integration_response(integration)


@integrations_router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    integration = await IntegrationService(db).get(ctx.organization_id, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return _integration_response(integration)


@integrations_router.patch("/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: uuid.UUID,
    payload: IntegrationUpdate,
    ctx: OrgContext = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    integration = await IntegrationService(db).get(ctx.organization_id, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    if payload.name is not None:
        integration.name = payload.name
    if payload.config is not None:
        integration.config = payload.config
    if payload.status is not None:
        integration.status = payload.status
    await db.flush()
    await db.commit()
    return _integration_response(integration)


@integrations_router.post("/{integration_id}/connect", response_model=IntegrationResponse)
async def connect_integration(
    integration_id: uuid.UUID,
    payload: IntegrationConnect,
    ctx: OrgContext = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    svc = IntegrationService(db)
    integration = await svc.get(ctx.organization_id, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    try:
        integration = await svc.connect(integration, payload.credential)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if payload.webhook_secret:
        from app.auth.encryption import encrypt_secret

        cfg = dict(integration.config or {})
        cfg["webhook_secret_encrypted"] = encrypt_secret(payload.webhook_secret)
        integration.config = cfg
        await db.flush()

    await record_activity(
        db,
        organization_id=ctx.organization_id,
        event_type="integration.connected",
        resource_type="integration",
        resource_id=str(integration.id),
        actor_id=ctx.user.id,
        metadata={"provider": integration.provider},
    )
    await db.commit()
    return _integration_response(integration)


@integrations_router.post("/{integration_id}/disconnect", response_model=IntegrationResponse)
async def disconnect_integration(
    integration_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.INTEGRATIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    svc = IntegrationService(db)
    integration = await svc.get(ctx.organization_id, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    integration = await svc.disconnect(integration)
    await db.commit()
    return _integration_response(integration)


@integrations_router.post("/{integration_id}/github/webhook")
async def github_incoming_webhook(
    integration_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive GitHub webhook events (signature verified)."""
    from sqlalchemy import select

    from app.models.platform import Integration

    svc = IntegrationService(db)
    result = await db.execute(select(Integration).where(Integration.id == integration_id))
    integration = result.scalar_one_or_none()
    if not integration or integration.provider != "github":
        raise HTTPException(status_code=404, detail="GitHub integration not found")

    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    event_name = request.headers.get("X-GitHub-Event", "")

    cfg = integration.config or {}
    secret_enc = cfg.get("webhook_secret_encrypted")
    if not secret_enc:
        raise HTTPException(status_code=401, detail="Webhook secret not configured")
    secret = decrypt_secret(secret_enc)
    if not IntegrationService.verify_github_webhook(body, signature, secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    import json

    payload = json.loads(body)
    from app.services.platform.cicd import CICDRegistry

    pipeline = CICDRegistry.normalize("github", payload)
    result_data = await svc.handle_github_event(integration, event_name, payload)
    if pipeline and pipeline.status.value in {"success", "failed"}:
        bus = EventBus(db)
        event_type = "deployment.completed" if pipeline.status.value == "success" else "deployment.failed"
        await bus.emit(
            organization_id=integration.organization_id,
            event_type=event_type,
            data={"deployment_id": pipeline.external_id, "provider": "github"},
            source="github",
        )
    await db.commit()
    return result_data


@automations_router.get("/templates", response_model=list[AutomationTemplateResponse])
async def list_templates(
    ctx: OrgContext = Depends(require_permission(Permission.AUTOMATIONS_MANAGE)),
):
    return [AutomationTemplateResponse(**t) for t in AutomationService.list_templates()]


@automations_router.get("/", response_model=list[AutomationResponse])
async def list_automations(
    ctx: OrgContext = Depends(require_permission(Permission.AUTOMATIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    items = await AutomationService(db).list_automations(ctx.organization_id)
    return [
        AutomationResponse(
            id=a.id,
            name=a.name,
            description=a.description,
            trigger_type=a.trigger_type,
            trigger_config=a.trigger_config or {},
            action_type=a.action_type,
            action_config=a.action_config or {},
            template_id=a.template_id,
            status=a.status,
            requires_approval=a.requires_approval,
            created_at=a.created_at,
        )
        for a in items
    ]


@automations_router.post("/", response_model=AutomationResponse, status_code=status.HTTP_201_CREATED)
async def create_automation(
    payload: AutomationCreate,
    ctx: OrgContext = Depends(require_permission(Permission.AUTOMATIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    automation = await AutomationService(db).create(
        organization_id=ctx.organization_id,
        name=payload.name,
        description=payload.description,
        trigger_type=payload.trigger_type,
        trigger_config=payload.trigger_config,
        action_type=payload.action_type,
        action_config=payload.action_config,
        template_id=payload.template_id,
        requires_approval=payload.requires_approval,
        created_by=ctx.user.id,
    )
    await record_activity(
        db,
        organization_id=ctx.organization_id,
        event_type="automation.created",
        resource_type="automation",
        resource_id=str(automation.id),
        actor_id=ctx.user.id,
    )
    await db.commit()
    return AutomationResponse(
        id=automation.id,
        name=automation.name,
        description=automation.description,
        trigger_type=automation.trigger_type,
        trigger_config=automation.trigger_config or {},
        action_type=automation.action_type,
        action_config=automation.action_config or {},
        template_id=automation.template_id,
        status=automation.status,
        requires_approval=automation.requires_approval,
        created_at=automation.created_at,
    )


@automations_router.get("/{automation_id}", response_model=AutomationResponse)
async def get_automation(
    automation_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.AUTOMATIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    automation = await AutomationService(db).get(ctx.organization_id, automation_id)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    return AutomationResponse(
        id=automation.id,
        name=automation.name,
        description=automation.description,
        trigger_type=automation.trigger_type,
        trigger_config=automation.trigger_config or {},
        action_type=automation.action_type,
        action_config=automation.action_config or {},
        template_id=automation.template_id,
        status=automation.status,
        requires_approval=automation.requires_approval,
        created_at=automation.created_at,
    )


@automations_router.patch("/{automation_id}", response_model=AutomationResponse)
async def update_automation(
    automation_id: uuid.UUID,
    payload: AutomationUpdate,
    ctx: OrgContext = Depends(require_permission(Permission.AUTOMATIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    automation = await AutomationService(db).get(ctx.organization_id, automation_id)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    if payload.name is not None:
        automation.name = payload.name
    if payload.description is not None:
        automation.description = payload.description
    if payload.trigger_config is not None:
        automation.trigger_config = payload.trigger_config
    if payload.action_config is not None:
        automation.action_config = payload.action_config
    if payload.status is not None:
        automation.status = payload.status
    if payload.requires_approval is not None:
        automation.requires_approval = payload.requires_approval
    await db.flush()
    await db.commit()
    return AutomationResponse(
        id=automation.id,
        name=automation.name,
        description=automation.description,
        trigger_type=automation.trigger_type,
        trigger_config=automation.trigger_config or {},
        action_type=automation.action_type,
        action_config=automation.action_config or {},
        template_id=automation.template_id,
        status=automation.status,
        requires_approval=automation.requires_approval,
        created_at=automation.created_at,
    )


@automations_router.post("/{automation_id}/execute", response_model=AutomationExecutionResponse)
async def execute_automation(
    automation_id: uuid.UUID,
    payload: AutomationExecuteRequest,
    ctx: OrgContext = Depends(require_permission(Permission.AUTOMATIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    automation = await AutomationService(db).get(ctx.organization_id, automation_id)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    execution = await AutomationService(db).execute(
        automation, context=payload.context, force=payload.force
    )
    await record_activity(
        db,
        organization_id=ctx.organization_id,
        event_type="automation.triggered",
        resource_type="automation",
        resource_id=str(automation.id),
        actor_id=ctx.user.id,
    )
    await db.commit()
    return AutomationExecutionResponse(
        id=execution.id,
        automation_id=execution.automation_id,
        event_id=execution.event_id,
        status=execution.status,
        trigger_summary=execution.trigger_summary,
        result_summary=execution.result_summary,
        error_message=execution.error_message,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        created_at=execution.created_at,
    )


@automations_router.get("/{automation_id}/executions", response_model=list[AutomationExecutionResponse])
async def list_executions(
    automation_id: uuid.UUID,
    limit: int = 50,
    ctx: OrgContext = Depends(require_permission(Permission.AUTOMATIONS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    automation = await AutomationService(db).get(ctx.organization_id, automation_id)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    executions = await AutomationService(db).list_executions(
        ctx.organization_id, automation_id=automation_id, limit=min(limit, 100)
    )
    return [
        AutomationExecutionResponse(
            id=e.id,
            automation_id=e.automation_id,
            event_id=e.event_id,
            status=e.status,
            trigger_summary=e.trigger_summary,
            result_summary=e.result_summary,
            error_message=e.error_message,
            started_at=e.started_at,
            completed_at=e.completed_at,
            created_at=e.created_at,
        )
        for e in executions
    ]


@developer_router.get("/activity", response_model=list[DeveloperActivityEntry])
async def developer_activity(
    limit: int = 50,
    ctx: OrgContext = Depends(require_permission(Permission.EVENTS_READ)),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.models.enterprise import ActivityEvent

    result = await db.execute(
        select(ActivityEvent)
        .where(
            ActivityEvent.organization_id == ctx.organization_id,
            ActivityEvent.event_type.in_([
                "webhook.created",
                "integration.connected",
                "automation.created",
                "automation.triggered",
                "api_key.created",
                "api_key.rotated",
            ]),
        )
        .order_by(ActivityEvent.created_at.desc())
        .limit(min(limit, 100))
    )
    return [
        DeveloperActivityEntry(
            event_type=e.event_type,
            resource_type=e.resource_type,
            resource_id=e.resource_id,
            timestamp=e.created_at,
            metadata=e.safe_metadata or {},
        )
        for e in result.scalars().all()
    ]


@developer_router.get("/overview")
async def developer_overview(
    ctx: OrgContext = Depends(require_permission(Permission.EVENTS_READ)),
    db: AsyncSession = Depends(get_db),
):
    webhooks = await WebhookService(db).list_endpoints(ctx.organization_id)
    integrations = await IntegrationService(db).list_integrations(ctx.organization_id)
    automations = await AutomationService(db).list_automations(ctx.organization_id)
    return {
        "event_types": len(EventCatalog.list_events()),
        "webhooks": len(webhooks),
        "integrations": len(integrations),
        "automations": len(automations),
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
    }
