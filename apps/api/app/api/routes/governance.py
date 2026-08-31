from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.org_context import OrgContext
from app.auth.rbac import Permission, require_permission
from app.db.base import get_db
from app.models.governance import (
    ApprovalRequest,
    ApprovalStatus,
    GovernanceEvent,
    GovernanceNotification,
    GovernancePolicy,
    PolicyStatus,
    PolicyType,
    PolicyVersion,
)
from app.schemas.governance import (
    ApprovalResponse,
    ApprovalReview,
    EventResponse,
    NotificationResponse,
    OverviewResponse,
    PolicyCreate,
    PolicyResponse,
    PolicyUpdate,
    PolicyVersionResponse,
    ReportResponse,
    SettingsResponse,
    SettingsUpdate,
    SimulateRequest,
    SimulateResponse,
)
from app.services.audit import (
    AUDIT_GOVERNANCE_APPROVAL,
    AUDIT_GOVERNANCE_POLICY_CREATED,
    AUDIT_GOVERNANCE_POLICY_DELETED,
    AUDIT_GOVERNANCE_POLICY_DISABLED,
    AUDIT_GOVERNANCE_POLICY_ENABLED,
    AUDIT_GOVERNANCE_POLICY_UPDATED,
    AuditService,
)
from app.services.capabilities import detect_chat_capabilities
from app.services.governance.classifier import classify_request
from app.services.governance.detection import categories_only, detect_sensitive, has_pii, has_secret
from app.services.governance.engine import PolicyAction, validate_rules
from app.services.governance.pipeline import (
    extract_text,
    get_or_create_settings,
    load_policies,
    policy_fingerprint,
)
from app.services.governance.risk import classify_risk
from app.services.governance.engine import PolicyRecord, evaluate_policies
from app.schemas.chat import ChatMessage

router = APIRouter(prefix="/governance", tags=["Governance"])

_VALID_TYPES = {t.value for t in PolicyType}
_VALID_STATUS = {s.value for s in PolicyStatus}
_VALID_ACTIONS = {a.value for a in PolicyAction}


def _validate_policy_fields(policy_type: str, status: str, action: str, rules: dict) -> None:
    if policy_type not in _VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid policy_type: {policy_type}")
    if status not in _VALID_STATUS:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    if action not in _VALID_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}")
    try:
        validate_rules(rules)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


async def _snapshot_version(
    db: AsyncSession,
    policy: GovernancePolicy,
    changed_by: uuid.UUID | None,
    summary: str | None,
) -> None:
    db.add(
        PolicyVersion(
            policy_id=policy.id,
            organization_id=policy.organization_id,
            version=policy.version,
            action=policy.action,
            rules=policy.rules or {},
            status=policy.status,
            priority=policy.priority,
            change_summary=summary,
            changed_by=changed_by,
        )
    )


@router.get("/policies", response_model=list[PolicyResponse])
async def list_policies(
    ctx: OrgContext = Depends(require_permission(Permission.GOVERNANCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GovernancePolicy)
        .where(GovernancePolicy.organization_id == ctx.organization_id)
        .order_by(GovernancePolicy.priority, GovernancePolicy.name)
    )
    return [PolicyResponse.model_validate(p) for p in result.scalars().all()]


@router.post("/policies", response_model=PolicyResponse, status_code=201)
async def create_policy(
    payload: PolicyCreate,
    ctx: OrgContext = Depends(require_permission(Permission.GOVERNANCE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    _validate_policy_fields(payload.policy_type, payload.status, payload.action, payload.rules)
    policy = GovernancePolicy(
        organization_id=ctx.organization_id,
        name=payload.name,
        description=payload.description,
        policy_type=payload.policy_type,
        status=payload.status,
        priority=payload.priority,
        rules=payload.rules,
        action=payload.action,
        created_by=ctx.user.id,
    )
    db.add(policy)
    await db.flush()
    await _snapshot_version(db, policy, ctx.user.id, "Created")
    await AuditService(db).log(
        AUDIT_GOVERNANCE_POLICY_CREATED,
        "governance_policy",
        str(policy.id),
        actor=ctx.user,
        organization_id=ctx.organization_id,
        metadata={"name": policy.name, "action": policy.action},
    )
    return PolicyResponse.model_validate(policy)


@router.get("/policies/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.GOVERNANCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    policy = await db.get(GovernancePolicy, policy_id)
    if not policy or policy.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Policy not found")
    return PolicyResponse.model_validate(policy)


@router.patch("/policies/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: uuid.UUID,
    payload: PolicyUpdate,
    ctx: OrgContext = Depends(require_permission(Permission.GOVERNANCE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    policy = await db.get(GovernancePolicy, policy_id)
    if not policy or policy.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Policy not found")
    data = payload.model_dump(exclude_unset=True)
    summary = data.pop("change_summary", None)
    new_type = data.get("policy_type", policy.policy_type)
    new_status = data.get("status", policy.status)
    new_action = data.get("action", policy.action)
    new_rules = data.get("rules", policy.rules)
    _validate_policy_fields(new_type, new_status, new_action, new_rules)
    old_status = policy.status
    for key, value in data.items():
        setattr(policy, key, value)
    policy.version = policy.version + 1
    await db.flush()
    await _snapshot_version(db, policy, ctx.user.id, summary or "Updated")
    audit = AuditService(db)
    await audit.log(
        AUDIT_GOVERNANCE_POLICY_UPDATED,
        "governance_policy",
        str(policy.id),
        actor=ctx.user,
        organization_id=ctx.organization_id,
        metadata={"version": policy.version},
    )
    if old_status != policy.status:
        action = (
            AUDIT_GOVERNANCE_POLICY_ENABLED
            if policy.status == PolicyStatus.ACTIVE
            else AUDIT_GOVERNANCE_POLICY_DISABLED
        )
        await audit.log(action, "governance_policy", str(policy.id), actor=ctx.user, organization_id=ctx.organization_id)
    return PolicyResponse.model_validate(policy)


@router.delete("/policies/{policy_id}", status_code=204)
async def delete_policy(
    policy_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.GOVERNANCE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    policy = await db.get(GovernancePolicy, policy_id)
    if not policy or policy.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Policy not found")
    await db.delete(policy)
    await AuditService(db).log(
        AUDIT_GOVERNANCE_POLICY_DELETED,
        "governance_policy",
        str(policy_id),
        actor=ctx.user,
        organization_id=ctx.organization_id,
        metadata={"name": policy.name},
    )
    return Response(status_code=204)


@router.get("/policies/{policy_id}/versions", response_model=list[PolicyVersionResponse])
async def list_policy_versions(
    policy_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.GOVERNANCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    policy = await db.get(GovernancePolicy, policy_id)
    if not policy or policy.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Policy not found")
    result = await db.execute(
        select(PolicyVersion)
        .where(
            PolicyVersion.policy_id == policy_id,
            PolicyVersion.organization_id == ctx.organization_id,
        )
        .order_by(PolicyVersion.version.desc())
    )
    return [PolicyVersionResponse.model_validate(v) for v in result.scalars().all()]


@router.get("/policies/{policy_id}/events", response_model=list[EventResponse])
async def policy_events(
    policy_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.GOVERNANCE_READ)),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
):
    policy = await db.get(GovernancePolicy, policy_id)
    if not policy or policy.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Policy not found")
    result = await db.execute(
        select(GovernanceEvent)
        .where(
            GovernanceEvent.organization_id == ctx.organization_id,
            GovernanceEvent.policy_id == policy_id,
        )
        .order_by(GovernanceEvent.created_at.desc())
        .limit(limit)
    )
    return [EventResponse.model_validate(e) for e in result.scalars().all()]


@router.post("/simulate", response_model=SimulateResponse)
async def simulate(
    payload: SimulateRequest,
    ctx: OrgContext = Depends(require_permission(Permission.GOVERNANCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate policies without calling an AI provider."""
    messages = [ChatMessage(**m) if isinstance(m, dict) else m for m in payload.messages]
    text = extract_text(messages, payload.input)
    settings = await get_or_create_settings(db, ctx.organization_id)
    detections = detect_sensitive(text, pii=settings.pii_detection_enabled, secrets=settings.secret_detection_enabled)
    caps = detect_chat_capabilities(messages, payload.tools, None, None, payload.stream)
    if payload.request_type == "embedding":
        caps = {"embeddings"}
    classification = classify_request(text, has_pii=has_pii(detections), has_secret=has_secret(detections))
    risk = classify_risk(
        classification=classification.classification,
        has_pii=has_pii(detections),
        has_secret=has_secret(detections),
        has_vision="vision" in caps,
        requested_model=payload.model,
    )
    policies = await load_policies(db, ctx.organization_id)
    records = [
        PolicyRecord(
            id=str(p.id),
            name=p.name,
            policy_type=p.policy_type,
            status=p.status,
            priority=p.priority,
            action=p.action,
            rules=p.rules or {},
            version=p.version,
        )
        for p in policies
    ]
    decision = evaluate_policies(
        records,
        {
            "risk_level": risk.level,
            "classification": classification.classification,
            "requested_model": payload.model,
            "capabilities": sorted(caps),
            "capability": sorted(caps),
            "has_pii": has_pii(detections),
            "has_secret": has_secret(detections),
            "detection_categories": categories_only(detections),
            "request_type": payload.request_type,
        },
    )
    r = decision.restrictions
    return SimulateResponse(
        decision=decision.action,
        reason=decision.reason,
        classification=classification.classification,
        risk_level=risk.level,
        risk_reasons=risk.reasons,
        detection_categories=categories_only(detections),
        matched_policies=[
            {
                "id": m.policy_id,
                "name": m.name,
                "type": m.policy_type,
                "action": m.action,
                "reason": m.reason,
                "priority": m.priority,
            }
            for m in decision.matched
        ],
        restrictions={
            "allowed_models": sorted(r.allowed_models) if r.allowed_models is not None else None,
            "blocked_models": sorted(r.blocked_models),
            "blocked_providers": sorted(r.blocked_providers),
            "local_only": r.local_only,
            "cloud_allowed": r.cloud_allowed,
        },
        policy_fingerprint=policy_fingerprint(records, settings),
    )


@router.get("/events", response_model=list[EventResponse])
async def list_events(
    ctx: OrgContext = Depends(require_permission(Permission.GOVERNANCE_READ)),
    db: AsyncSession = Depends(get_db),
    event_type: str | None = None,
    risk_level: str | None = None,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=500),
):
    start = datetime.now(UTC) - timedelta(days=days)
    query = select(GovernanceEvent).where(
        GovernanceEvent.organization_id == ctx.organization_id,
        GovernanceEvent.created_at >= start,
    )
    if event_type:
        query = query.where(GovernanceEvent.event_type == event_type)
    if risk_level:
        query = query.where(GovernanceEvent.risk_level == risk_level)
    result = await db.execute(query.order_by(GovernanceEvent.created_at.desc()).limit(limit))
    return [EventResponse.model_validate(e) for e in result.scalars().all()]


@router.get("/overview", response_model=OverviewResponse)
async def overview(
    ctx: OrgContext = Depends(require_permission(Permission.GOVERNANCE_READ)),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    org = ctx.organization_id
    start = datetime.now(UTC) - timedelta(days=days)
    active = await db.scalar(
        select(func.count()).select_from(GovernancePolicy).where(
            GovernancePolicy.organization_id == org,
            GovernancePolicy.status == PolicyStatus.ACTIVE,
        )
    )
    blocked = await db.scalar(
        select(func.count()).select_from(GovernanceEvent).where(
            GovernanceEvent.organization_id == org,
            GovernanceEvent.event_type == "policy.blocked",
            GovernanceEvent.created_at >= start,
        )
    )
    warnings = await db.scalar(
        select(func.count()).select_from(GovernanceEvent).where(
            GovernanceEvent.organization_id == org,
            GovernanceEvent.event_type == "policy.warned",
            GovernanceEvent.created_at >= start,
        )
    )
    sensitive = await db.scalar(
        select(func.count()).select_from(GovernanceEvent).where(
            GovernanceEvent.organization_id == org,
            GovernanceEvent.event_type == "sensitive_data.detected",
            GovernanceEvent.created_at >= start,
        )
    )
    pending = await db.scalar(
        select(func.count()).select_from(ApprovalRequest).where(
            ApprovalRequest.organization_id == org,
            ApprovalRequest.status == ApprovalStatus.PENDING,
        )
    )
    risk_rows = await db.execute(
        select(GovernanceEvent.risk_level, func.count())
        .where(GovernanceEvent.organization_id == org, GovernanceEvent.created_at >= start)
        .group_by(GovernanceEvent.risk_level)
    )
    risk_distribution = {row[0] or "UNKNOWN": row[1] for row in risk_rows.all()}
    top_rows = await db.execute(
        select(GovernanceEvent.policy_name, func.count())
        .where(
            GovernanceEvent.organization_id == org,
            GovernanceEvent.created_at >= start,
            GovernanceEvent.policy_name.is_not(None),
        )
        .group_by(GovernanceEvent.policy_name)
        .order_by(func.count().desc())
        .limit(5)
    )
    recent = await db.execute(
        select(GovernanceEvent)
        .where(GovernanceEvent.organization_id == org)
        .order_by(GovernanceEvent.created_at.desc())
        .limit(15)
    )
    return OverviewResponse(
        active_policies=int(active or 0),
        blocked_requests=int(blocked or 0),
        warnings=int(warnings or 0),
        sensitive_events=int(sensitive or 0),
        pending_approvals=int(pending or 0),
        risk_distribution=risk_distribution,
        top_policies=[{"name": n, "count": c} for n, c in top_rows.all()],
        recent_events=[EventResponse.model_validate(e) for e in recent.scalars().all()],
    )


@router.get("/reports", response_model=ReportResponse)
async def reports(
    ctx: OrgContext = Depends(require_permission(Permission.GOVERNANCE_READ)),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    risk_level: str | None = None,
    event_type: str | None = None,
):
    start = datetime.now(UTC) - timedelta(days=days)
    filters = [
        GovernanceEvent.organization_id == ctx.organization_id,
        GovernanceEvent.created_at >= start,
    ]
    if risk_level:
        filters.append(GovernanceEvent.risk_level == risk_level)
    if event_type:
        filters.append(GovernanceEvent.event_type == event_type)

    async def count_type(etype: str) -> int:
        q = [GovernanceEvent.organization_id == ctx.organization_id, GovernanceEvent.created_at >= start, GovernanceEvent.event_type == etype]
        if risk_level:
            q.append(GovernanceEvent.risk_level == risk_level)
        val = await db.scalar(select(func.count()).select_from(GovernanceEvent).where(*q))
        return int(val or 0)

    type_rows = await db.execute(
        select(GovernanceEvent.event_type, func.count()).where(*filters).group_by(GovernanceEvent.event_type)
    )
    risk_rows = await db.execute(
        select(GovernanceEvent.risk_level, func.count()).where(*filters).group_by(GovernanceEvent.risk_level)
    )
    approvals = await db.scalar(
        select(func.count()).select_from(ApprovalRequest).where(
            ApprovalRequest.organization_id == ctx.organization_id,
            ApprovalRequest.created_at >= start,
        )
    )
    return ReportResponse(
        start=start,
        end=datetime.now(UTC),
        policy_matches=int((await db.scalar(select(func.count()).select_from(GovernanceEvent).where(*filters))) or 0),
        blocked_requests=await count_type("policy.blocked"),
        warnings=await count_type("policy.warned"),
        sensitive_data_events=await count_type("sensitive_data.detected"),
        approvals=int(approvals or 0),
        by_risk={r or "UNKNOWN": c for r, c in risk_rows.all()},
        by_event_type={t: c for t, c in type_rows.all()},
    )


@router.get("/reports/export")
async def export_reports(
    ctx: OrgContext = Depends(require_permission(Permission.GOVERNANCE_READ)),
    db: AsyncSession = Depends(get_db),
    fmt: str = Query("json", pattern="^(json|csv)$"),
    days: int = Query(30, ge=1, le=365),
):
    start = datetime.now(UTC) - timedelta(days=days)
    result = await db.execute(
        select(GovernanceEvent)
        .where(
            GovernanceEvent.organization_id == ctx.organization_id,
            GovernanceEvent.created_at >= start,
        )
        .order_by(GovernanceEvent.created_at.desc())
        .limit(2000)
    )
    events = list(result.scalars().all())
    rows = [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "decision": e.decision,
            "policy_name": e.policy_name,
            "risk_level": e.risk_level,
            "classification": e.classification,
            "reason": e.reason,
            "detection_categories": e.detection_categories,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=["id", "event_type", "decision", "policy_name", "risk_level", "classification", "reason", "created_at"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in writer.fieldnames})
        return Response(content=buf.getvalue(), media_type="text/csv")
    return {"events": rows}


@router.get("/approvals", response_model=list[ApprovalResponse])
async def list_approvals(
    ctx: OrgContext = Depends(require_permission(Permission.GOVERNANCE_READ)),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
):
    await _expire_stale(db, ctx.organization_id)
    query = select(ApprovalRequest).where(ApprovalRequest.organization_id == ctx.organization_id)
    if status_filter:
        query = query.where(ApprovalRequest.status == status_filter)
    result = await db.execute(query.order_by(ApprovalRequest.created_at.desc()).limit(200))
    return [ApprovalResponse.model_validate(a) for a in result.scalars().all()]


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalResponse)
async def approve_request(
    approval_id: uuid.UUID,
    payload: ApprovalReview,
    ctx: OrgContext = Depends(require_permission(Permission.GOVERNANCE_APPROVE)),
    db: AsyncSession = Depends(get_db),
):
    return await _review(db, ctx, approval_id, ApprovalStatus.APPROVED, payload.comment)


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalResponse)
async def reject_request(
    approval_id: uuid.UUID,
    payload: ApprovalReview,
    ctx: OrgContext = Depends(require_permission(Permission.GOVERNANCE_APPROVE)),
    db: AsyncSession = Depends(get_db),
):
    return await _review(db, ctx, approval_id, ApprovalStatus.REJECTED, payload.comment)


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    ctx: OrgContext = Depends(require_permission(Permission.GOVERNANCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    settings = await get_or_create_settings(db, ctx.organization_id)
    return SettingsResponse.model_validate(settings)


@router.patch("/settings", response_model=SettingsResponse)
async def update_settings(
    payload: SettingsUpdate,
    ctx: OrgContext = Depends(require_permission(Permission.GOVERNANCE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    settings = await get_or_create_settings(db, ctx.organization_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, key, value)
    await db.flush()
    await AuditService(db).log(
        "governance.settings_updated",
        "governance_settings",
        str(ctx.organization_id),
        actor=ctx.user,
        organization_id=ctx.organization_id,
    )
    return SettingsResponse.model_validate(settings)


@router.get("/notifications", response_model=list[NotificationResponse])
async def list_notifications(
    ctx: OrgContext = Depends(require_permission(Permission.GOVERNANCE_READ)),
    db: AsyncSession = Depends(get_db),
    unread_only: bool = False,
):
    query = select(GovernanceNotification).where(
        GovernanceNotification.organization_id == ctx.organization_id
    )
    if unread_only:
        query = query.where(GovernanceNotification.is_read == False)  # noqa: E712
    result = await db.execute(query.order_by(GovernanceNotification.created_at.desc()).limit(50))
    return [NotificationResponse.model_validate(n) for n in result.scalars().all()]


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.GOVERNANCE_READ)),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(GovernanceNotification, notification_id)
    if not item or item.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Notification not found")
    item.is_read = True
    await db.flush()
    return NotificationResponse.model_validate(item)


async def _expire_stale(db: AsyncSession, org_id: uuid.UUID) -> None:
    now = datetime.now(UTC)
    result = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.organization_id == org_id,
            ApprovalRequest.status == ApprovalStatus.PENDING,
            ApprovalRequest.expires_at.is_not(None),
            ApprovalRequest.expires_at < now,
        )
    )
    for row in result.scalars().all():
        row.status = ApprovalStatus.EXPIRED


async def _review(
    db: AsyncSession,
    ctx: OrgContext,
    approval_id: uuid.UUID,
    status: str,
    comment: str | None,
) -> ApprovalResponse:
    await _expire_stale(db, ctx.organization_id)
    approval = await db.get(ApprovalRequest, approval_id)
    if not approval or approval.organization_id != ctx.organization_id:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=409, detail=f"Approval is {approval.status}")
    approval.status = status
    approval.reviewer_id = ctx.user.id
    approval.review_comment = comment
    approval.reviewed_at = datetime.now(UTC)
    await db.flush()
    await AuditService(db).log(
        AUDIT_GOVERNANCE_APPROVAL,
        "governance_approval",
        str(approval.id),
        actor=ctx.user,
        organization_id=ctx.organization_id,
        metadata={"status": status},
    )
    return ApprovalResponse.model_validate(approval)
