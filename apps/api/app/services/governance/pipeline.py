"""Pre- and post-request governance pipeline."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey
from app.models.governance import (
    ApprovalRequest,
    ApprovalStatus,
    GovernanceEvent,
    GovernanceNotification,
    GovernancePolicy,
    GovernanceSettings,
    PolicyAction,
)
from app.models.user import User
from app.services.audit import AuditService
from app.services.governance.classifier import classify_request
from app.services.governance.detection import (
    categories_only,
    detect_sensitive,
    has_pii as detections_have_pii,
    has_secret as detections_have_secret,
)
from app.services.governance.engine import (
    EngineDecision,
    GovernanceRestrictions,
    PolicyRecord,
    candidate_allowed,
    evaluate_policies,
)
from app.services.governance.redaction import redact_text, replacement_for
from app.services.governance.risk import classify_risk
from app.services.governance.safety import get_safety_backend
from app.services.metrics import record_governance_event

LOCAL_PROVIDER_TYPES = frozenset({"ollama", "lmstudio"})


@dataclass
class GovernanceContext:
    decision: str
    reason: str
    classification: str
    risk_level: str
    risk_reasons: list[str]
    matched: list
    restrictions: GovernanceRestrictions
    detections: list
    detection_labels: list[str]
    policy_fingerprint: str
    redacted_text: str | None = None
    should_redact_prompt: bool = False
    should_redact_response: bool = False
    approval_id: str | None = None
    request_fingerprint: str = ""
    settings: GovernanceSettings | None = None


def extract_text(messages: list | None, extra: str | None = None) -> str:
    parts: list[str] = []
    if extra:
        parts.append(extra)
    for msg in messages or []:
        content = msg.content if hasattr(msg, "content") else (msg.get("content") if isinstance(msg, dict) else None)
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text") or ""))
                elif isinstance(item, str):
                    parts.append(item)
    return "\n".join(parts)


def request_fingerprint(model: str, text: str) -> str:
    payload = json.dumps({"model": model, "text": text}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def policy_fingerprint(policies: list[PolicyRecord], settings: GovernanceSettings | None) -> str:
    items = [(p.id, p.version, p.status, p.action, p.priority) for p in policies]
    items.sort()
    settings_stamp = ""
    if settings:
        settings_stamp = str(settings.updated_at)
    raw = json.dumps({"policies": items, "settings": settings_stamp}, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _to_records(policies: list[GovernancePolicy]) -> list[PolicyRecord]:
    return [
        PolicyRecord(
            id=str(p.id),
            name=p.name,
            policy_type=p.policy_type,
            status=p.status,
            priority=p.priority,
            action=p.action,
            rules=p.rules or {},
            version=p.version,
            organization_id=str(p.organization_id),
        )
        for p in policies
    ]


async def load_policies(db: AsyncSession, org_id: uuid.UUID) -> list[GovernancePolicy]:
    result = await db.execute(
        select(GovernancePolicy).where(GovernancePolicy.organization_id == org_id)
    )
    return list(result.scalars().all())


async def get_or_create_settings(db: AsyncSession, org_id: uuid.UUID) -> GovernanceSettings:
    result = await db.execute(
        select(GovernanceSettings).where(GovernanceSettings.organization_id == org_id)
    )
    settings = result.scalar_one_or_none()
    if settings:
        return settings
    settings = GovernanceSettings(organization_id=org_id)
    db.add(settings)
    await db.flush()
    return settings


async def log_event(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    event_type: str,
    decision: str | None = None,
    policy_id: uuid.UUID | None = None,
    policy_name: str | None = None,
    policy_type: str | None = None,
    reason: str | None = None,
    risk_level: str | None = None,
    classification: str | None = None,
    detection_categories: list[str] | None = None,
    requested_model: str | None = None,
    request_id: str | None = None,
    actor_id: uuid.UUID | None = None,
    api_key_id: uuid.UUID | None = None,
    metadata: dict | None = None,
) -> GovernanceEvent:
    event = GovernanceEvent(
        organization_id=org_id,
        event_type=event_type,
        decision=decision,
        policy_id=policy_id,
        policy_name=policy_name,
        policy_type=policy_type,
        reason=reason,
        risk_level=risk_level,
        classification=classification,
        detection_categories=detection_categories,
        requested_model=requested_model,
        request_id=request_id,
        actor_id=actor_id,
        api_key_id=api_key_id,
        metadata_=metadata,
    )
    db.add(event)
    await db.flush()
    record_governance_event(event_type, decision or "none")
    return event


async def notify(
    db: AsyncSession,
    org_id: uuid.UUID,
    title: str,
    body: str,
    severity: str,
    event_id: uuid.UUID | None = None,
) -> None:
    db.add(
        GovernanceNotification(
            organization_id=org_id,
            title=title,
            body=body,
            severity=severity,
            event_id=event_id,
        )
    )


def apply_settings_restrictions(settings: GovernanceSettings, restrictions: GovernanceRestrictions) -> None:
    if not settings.allow_cloud_providers:
        restrictions.cloud_allowed = False
    if settings.require_local_for_high_risk:
        # applied later when risk is high
        pass
    if not settings.allow_local_providers:
        restrictions.blocked_provider_types.update(LOCAL_PROVIDER_TYPES)


def raise_blocked(reason: str, *, admin_detail: dict | None = None) -> None:
    detail: dict[str, Any] = {
        "code": "POLICY_DENIED",
        "message": "Request blocked by organization policy.",
        "type": "governance_error",
    }
    if admin_detail:
        detail["governance"] = admin_detail
    raise HTTPException(status_code=403, detail=detail)


async def evaluate_pre_request(
    db: AsyncSession,
    *,
    org_id: uuid.UUID | None,
    user: User | None,
    api_key: APIKey | None,
    requested_model: str,
    messages: list | None,
    extra_text: str | None = None,
    capabilities: set[str] | None = None,
    request_type: str = "chat",
    endpoint: str = "/v1/chat/completions",
    request_id: str | None = None,
    approval_id: str | None = None,
    expose_details: bool = False,
) -> GovernanceContext:
    if org_id is None:
        return GovernanceContext(
            decision=PolicyAction.ALLOW,
            reason="No organization context — governance skipped",
            classification="GENERAL",
            risk_level="LOW",
            risk_reasons=["No organization"],
            matched=[],
            restrictions=GovernanceRestrictions(),
            detections=[],
            detection_labels=[],
            policy_fingerprint="none",
        )

    settings = await get_or_create_settings(db, org_id)
    text = extract_text(messages, extra_text)
    detections = detect_sensitive(
        text,
        pii=settings.pii_detection_enabled,
        secrets=settings.secret_detection_enabled,
    )
    pii = detections_have_pii(detections)
    secrets = detections_have_secret(detections)
    labels = categories_only(detections)
    classification = classify_request(text, has_pii=pii, has_secret=secrets)
    risk = classify_risk(
        classification=classification.classification,
        has_pii=pii,
        has_secret=secrets,
        has_vision="vision" in (capabilities or set()),
        requested_model=requested_model,
    )

    policies = await load_policies(db, org_id)
    records = _to_records(policies)
    fingerprint = policy_fingerprint(records, settings)
    req_fp = request_fingerprint(requested_model, text)

    context = {
        "risk_level": risk.level,
        "classification": classification.classification,
        "requested_model": requested_model,
        "capability": sorted(capabilities or []),
        "capabilities": sorted(capabilities or []),
        "has_pii": pii,
        "has_secret": secrets,
        "detection_categories": labels,
        "api_key_id": str(api_key.id) if api_key else None,
        "request_type": request_type,
        "endpoint": endpoint,
        "deployment_type": "unknown",
    }
    decision: EngineDecision = evaluate_policies(records, context)
    apply_settings_restrictions(settings, decision.restrictions)
    if settings.require_local_for_high_risk and risk.level in {"HIGH", "CRITICAL"}:
        decision.restrictions.local_only = True
    if settings.block_sensitive_to_cloud and (pii or secrets or classification.classification in {"PERSONAL_DATA", "SENSITIVE", "HIGH_RISK"}):
        decision.restrictions.local_only = True
        decision.restrictions.cloud_allowed = False

    action = decision.action
    if settings.block_on_secret and secrets:
        action = PolicyAction.DENY
        decision.reason = "Secret-like material detected"

    if capabilities and decision.restrictions.blocked_capabilities:
        blocked = set(capabilities) & decision.restrictions.blocked_capabilities
        if blocked:
            action = PolicyAction.DENY
            decision.reason = f"Blocked capabilities: {', '.join(sorted(blocked))}"

    safety = get_safety_backend().evaluate(text) if settings.content_safety_enabled else None
    if safety and not safety.allowed:
        action = PolicyAction.DENY
        decision.reason = "Content safety policy blocked this request"

    should_redact = settings.redact_prompts or action == PolicyAction.REDACT
    if action == PolicyAction.REDACT:
        action = PolicyAction.ALLOW

    if approval_id:
        approved = await _consume_approval(db, org_id, approval_id, req_fp)
        if approved:
            action = PolicyAction.ALLOW
            decision.reason = "Approved request replay"

    ctx = GovernanceContext(
        decision=action,
        reason=decision.reason,
        classification=classification.classification,
        risk_level=risk.level,
        risk_reasons=risk.reasons,
        matched=decision.matched,
        restrictions=decision.restrictions,
        detections=detections,
        detection_labels=labels,
        policy_fingerprint=fingerprint,
        should_redact_prompt=should_redact,
        should_redact_response=settings.redact_responses,
        request_fingerprint=req_fp,
        settings=settings,
        redacted_text=redact_text(text, detections, replacement_for) if should_redact else None,
    )

    actor_id = user.id if user else None
    api_key_id = api_key.id if api_key else None

    if labels:
        event = await log_event(
            db,
            org_id=org_id,
            event_type="sensitive_data.detected",
            decision=action,
            reason="Sensitive categories detected",
            risk_level=risk.level,
            classification=classification.classification,
            detection_categories=labels,
            requested_model=requested_model,
            request_id=request_id,
            actor_id=actor_id,
            api_key_id=api_key_id,
        )
        if secrets:
            await notify(db, org_id, "Secret detection", "Secret-like material was detected in a request.", "high", event.id)
        elif pii:
            await notify(db, org_id, "PII detection", "Possible PII was detected in a request.", "medium", event.id)

    if should_redact and detections:
        await log_event(
            db,
            org_id=org_id,
            event_type="redaction.applied",
            decision=action,
            reason="Prompt redaction applied before provider call",
            risk_level=risk.level,
            classification=classification.classification,
            detection_categories=labels,
            requested_model=requested_model,
            request_id=request_id,
            actor_id=actor_id,
            api_key_id=api_key_id,
        )

    top = decision.matched[-1] if decision.matched else None
    policy_uuid = uuid.UUID(top.policy_id) if top else None

    if action == PolicyAction.WARN:
        await log_event(
            db,
            org_id=org_id,
            event_type="policy.warned",
            decision=action,
            policy_id=policy_uuid,
            policy_name=top.name if top else None,
            policy_type=top.policy_type if top else None,
            reason=decision.reason,
            risk_level=risk.level,
            classification=classification.classification,
            requested_model=requested_model,
            request_id=request_id,
            actor_id=actor_id,
            api_key_id=api_key_id,
        )
    elif action == PolicyAction.DENY:
        event = await log_event(
            db,
            org_id=org_id,
            event_type="policy.blocked",
            decision=action,
            policy_id=policy_uuid,
            policy_name=top.name if top else None,
            policy_type=top.policy_type if top else None,
            reason=decision.reason,
            risk_level=risk.level,
            classification=classification.classification,
            detection_categories=labels,
            requested_model=requested_model,
            request_id=request_id,
            actor_id=actor_id,
            api_key_id=api_key_id,
        )
        await notify(db, org_id, "Policy violation", "A request was blocked by organization policy.", "high", event.id)
        await AuditService(db).log(
            "governance.request_blocked",
            "governance_policy",
            str(policy_uuid) if policy_uuid else None,
            actor=user,
            organization_id=org_id,
            metadata={"reason": decision.reason, "risk_level": risk.level},
        )
        raise_blocked(
            decision.reason,
            admin_detail={
                "reason": decision.reason,
                "matched": [
                    {"name": m.name, "action": m.action, "type": m.policy_type}
                    for m in decision.matched
                ],
            }
            if expose_details
            else None,
        )
    elif action == PolicyAction.REQUIRE_APPROVAL:
        if not settings.approval_enabled:
            raise_blocked("Approval required but approval workflow is disabled.")
        approval = await _create_approval(
            db,
            org_id=org_id,
            settings=settings,
            ctx=ctx,
            requested_model=requested_model,
            requester_id=actor_id,
            request_type=request_type,
            policy_id=policy_uuid,
            policy_name=top.name if top else None,
        )
        ctx.approval_id = str(approval.id)
        await log_event(
            db,
            org_id=org_id,
            event_type="approval.requested",
            decision=action,
            policy_id=policy_uuid,
            policy_name=top.name if top else None,
            reason=decision.reason,
            risk_level=risk.level,
            classification=classification.classification,
            requested_model=requested_model,
            request_id=request_id,
            actor_id=actor_id,
            api_key_id=api_key_id,
            metadata={"approval_id": str(approval.id)},
        )
        await notify(
            db,
            org_id,
            "Approval required",
            "A high-risk request is waiting for review.",
            "high",
        )
        raise HTTPException(
            status_code=403,
            detail={
                "code": "APPROVAL_REQUIRED",
                "message": "Request requires approval before provider execution. Replay with X-ModelBridge-Approval-ID after approval.",
                "type": "governance_error",
                "approval_id": str(approval.id),
                "status": approval.status,
            },
        )

    if risk.level in {"HIGH", "CRITICAL"} and action == PolicyAction.ALLOW:
        await notify(db, org_id, "High risk request", "A high-risk request was allowed to proceed.", "medium")

    return ctx


async def _create_approval(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    settings: GovernanceSettings,
    ctx: GovernanceContext,
    requested_model: str,
    requester_id: uuid.UUID | None,
    request_type: str,
    policy_id: uuid.UUID | None,
    policy_name: str | None,
) -> ApprovalRequest:
    expires = datetime.now(UTC) + timedelta(hours=settings.approval_ttl_hours)
    approval = ApprovalRequest(
        organization_id=org_id,
        status=ApprovalStatus.PENDING,
        request_type=request_type,
        risk_level=ctx.risk_level,
        classification=ctx.classification,
        matched_policy_id=policy_id,
        matched_policy_name=policy_name,
        requested_model=requested_model,
        fingerprint=ctx.request_fingerprint,
        requester_id=requester_id,
        expires_at=expires,
        safe_snapshot={
            "model": requested_model,
            "risk_level": ctx.risk_level,
            "classification": ctx.classification,
            "detection_categories": ctx.detection_labels,
            "redacted_preview": (ctx.redacted_text or "")[:500],
        },
    )
    db.add(approval)
    await db.flush()
    return approval


async def _consume_approval(
    db: AsyncSession, org_id: uuid.UUID, approval_id: str, fingerprint: str
) -> bool:
    try:
        aid = uuid.UUID(approval_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid approval id")
    result = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.id == aid,
            ApprovalRequest.organization_id == org_id,
        )
    )
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    now = datetime.now(UTC)
    if approval.status == ApprovalStatus.PENDING and approval.expires_at and approval.expires_at < now:
        approval.status = ApprovalStatus.EXPIRED
        await db.flush()
    if approval.status != ApprovalStatus.APPROVED:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "APPROVAL_NOT_APPROVED",
                "message": f"Approval is {approval.status}",
                "type": "governance_error",
            },
        )
    if approval.fingerprint != fingerprint:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "APPROVAL_FINGERPRINT_MISMATCH",
                "message": "Request does not match the approved payload",
                "type": "governance_error",
            },
        )
    return True


def redact_messages(messages: list, detections_text: str | None, original_text: str) -> list:
    """Replace message string content using full-text redaction mapping.

    Original stored request logs are not mutated here. Only the in-memory
    provider-bound copy should be passed through this helper.
    """
    if detections_text is None:
        return messages
    redacted_full = detections_text
    # When extract_text joined with newlines, apply per-message detection again.
    from app.services.governance.detection import detect_sensitive

    out = []
    for msg in messages:
        if hasattr(msg, "model_copy"):
            clone = msg.model_copy(deep=True)
            if isinstance(clone.content, str):
                dets = detect_sensitive(clone.content)
                clone.content = redact_text(clone.content, dets, replacement_for)
            out.append(clone)
        elif isinstance(msg, dict):
            item = dict(msg)
            if isinstance(item.get("content"), str):
                dets = detect_sensitive(item["content"])
                item["content"] = redact_text(item["content"], dets, replacement_for)
            out.append(item)
        else:
            out.append(msg)
    _ = redacted_full
    _ = original_text
    return out


async def evaluate_response(
    db: AsyncSession,
    *,
    org_id: uuid.UUID | None,
    text: str,
    ctx: GovernanceContext,
    request_id: str | None = None,
    requested_model: str | None = None,
    actor_id: uuid.UUID | None = None,
) -> str:
    if org_id is None or not ctx.settings:
        return text
    settings = ctx.settings
    detections = detect_sensitive(
        text,
        pii=settings.pii_detection_enabled,
        secrets=settings.secret_detection_enabled,
    )
    policies = [p for p in ctx.matched if p.policy_type == "response"]
    if detections and (settings.redact_responses or ctx.should_redact_response or any(p.action == "redact" for p in policies)):
        await log_event(
            db,
            org_id=org_id,
            event_type="response.redacted",
            decision="redact",
            reason="Response redaction applied",
            risk_level=ctx.risk_level,
            classification=ctx.classification,
            detection_categories=categories_only(detections),
            requested_model=requested_model,
            request_id=request_id,
            actor_id=actor_id,
        )
        return redact_text(text, detections, replacement_for)

    labels = categories_only(detections)
    if detections_have_secret(detections) and settings.block_on_secret:
        await log_event(
            db,
            org_id=org_id,
            event_type="policy.blocked",
            decision="deny",
            reason="Secret-like material in model response",
            risk_level=ctx.risk_level,
            classification=ctx.classification,
            detection_categories=labels,
            requested_model=requested_model,
            request_id=request_id,
            actor_id=actor_id,
        )
        raise HTTPException(
            status_code=403,
            detail={
                "code": "RESPONSE_BLOCKED",
                "message": "Response blocked by organization policy.",
                "type": "governance_error",
            },
        )

    safety = get_safety_backend().evaluate(text) if settings.content_safety_enabled else None
    if safety and not safety.allowed:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "RESPONSE_BLOCKED",
                "message": "Response blocked by content safety policy.",
                "type": "governance_error",
            },
        )
    return text


def filter_targets(targets: list, restrictions: GovernanceRestrictions) -> list:
    kept = []
    for target in targets:
        provider = target.provider
        model_id = target.resolved_model
        is_local = provider.type in LOCAL_PROVIDER_TYPES
        ok, _reason = candidate_allowed(
            model_id=model_id,
            provider_name=provider.name,
            provider_type=str(provider.type),
            is_local=is_local,
            restrictions=restrictions,
        )
        if ok:
            kept.append(target)
    return kept
