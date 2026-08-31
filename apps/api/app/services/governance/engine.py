"""Structured policy engine — no arbitrary code execution.

Precedence (documented in docs/governance.md):
1. Policies are evaluated in ascending priority (1 before 100).
2. Only ACTIVE policies participate in enforcement.
3. Organization-scoped DENY cannot be overridden by API-key ALLOW.
4. When matched actions conflict, severity wins:
   DENY > REQUIRE_APPROVAL > REDACT > WARN > ALLOW
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.governance import PolicyAction, PolicyStatus, PolicyType

SEVERITY = {
    PolicyAction.ALLOW: 0,
    PolicyAction.WARN: 1,
    PolicyAction.REDACT: 2,
    PolicyAction.REQUIRE_APPROVAL: 3,
    PolicyAction.DENY: 4,
}

ALLOWED_FIELDS = frozenset({
    "risk_level",
    "classification",
    "requested_model",
    "provider_type",
    "provider_name",
    "capability",
    "capabilities",
    "has_pii",
    "has_secret",
    "detection_categories",
    "api_key_id",
    "deployment_type",
    "request_type",
    "endpoint",
})

ALLOWED_OPERATORS = frozenset({
    "equals",
    "not_equals",
    "in",
    "not_in",
    "contains",
    "greater_than",
    "less_than",
})


class PolicyValidationError(ValueError):
    pass


@dataclass
class PolicyRecord:
    id: str
    name: str
    policy_type: str
    status: str
    priority: int
    action: str
    rules: dict
    version: int = 1
    organization_id: str | None = None


@dataclass
class MatchedPolicy:
    policy_id: str
    name: str
    policy_type: str
    action: str
    reason: str
    priority: int
    version: int = 1


@dataclass
class GovernanceRestrictions:
    allowed_models: set[str] | None = None
    blocked_models: set[str] = field(default_factory=set)
    allowed_providers: set[str] | None = None
    blocked_providers: set[str] = field(default_factory=set)
    allowed_provider_types: set[str] | None = None
    blocked_provider_types: set[str] = field(default_factory=set)
    blocked_capabilities: set[str] = field(default_factory=set)
    local_only: bool = False
    cloud_allowed: bool = True
    data_residency_policy: str | None = None


@dataclass
class EngineDecision:
    action: str
    reason: str
    matched: list[MatchedPolicy] = field(default_factory=list)
    restrictions: GovernanceRestrictions = field(default_factory=GovernanceRestrictions)
    org_denied: bool = False


def validate_rules(rules: dict | None) -> dict:
    if rules is None:
        return {}
    if not isinstance(rules, dict):
        raise PolicyValidationError("rules must be an object")
    conditions = rules.get("conditions")
    if conditions is not None:
        if not isinstance(conditions, list):
            raise PolicyValidationError("rules.conditions must be a list")
        for cond in conditions:
            if not isinstance(cond, dict):
                raise PolicyValidationError("each condition must be an object")
            field = cond.get("field")
            operator = cond.get("operator")
            if field not in ALLOWED_FIELDS:
                raise PolicyValidationError(f"unsupported field: {field}")
            if operator not in ALLOWED_OPERATORS:
                raise PolicyValidationError(f"unsupported operator: {operator}")
            if "value" not in cond:
                raise PolicyValidationError("condition requires value")
    match = rules.get("match", "all")
    if match not in ("all", "any"):
        raise PolicyValidationError("rules.match must be 'all' or 'any'")
    for key in (
        "allowed_models",
        "blocked_models",
        "allowed_providers",
        "blocked_providers",
        "allowed_provider_types",
        "blocked_provider_types",
        "blocked_capabilities",
        "api_key_ids",
    ):
        if key in rules and not isinstance(rules[key], list):
            raise PolicyValidationError(f"{key} must be a list of strings")
    return rules


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "equals":
        if isinstance(actual, list):
            return expected in actual or str(expected) in [str(x) for x in actual]
        return actual == expected or str(actual).lower() == str(expected).lower()
    if operator == "not_equals":
        return not _compare(actual, "equals", expected)
    if operator == "in":
        expected_list = [str(x).lower() if not isinstance(x, bool) else x for x in _as_list(expected)]
        if isinstance(actual, list):
            return any(str(a).lower() in expected_list for a in actual)
        return str(actual).lower() in expected_list
    if operator == "not_in":
        return not _compare(actual, "in", expected)
    if operator == "contains":
        if isinstance(actual, list):
            return str(expected).lower() in [str(x).lower() for x in actual]
        return str(expected).lower() in str(actual).lower()
    if operator == "greater_than":
        try:
            return float(actual) > float(expected)
        except (TypeError, ValueError):
            return False
    if operator == "less_than":
        try:
            return float(actual) < float(expected)
        except (TypeError, ValueError):
            return False
    return False


def condition_matches(condition: dict, context: dict[str, Any]) -> bool:
    field = condition.get("field")
    operator = condition.get("operator", "equals")
    expected = condition.get("value")
    actual = context.get(field)
    if field == "capability":
        actual = context.get("capabilities") or context.get("capability")
    return _compare(actual, operator, expected)


def rules_match(rules: dict, context: dict[str, Any]) -> bool:
    conditions = rules.get("conditions") or []
    if not conditions:
        return True
    match = rules.get("match", "all")
    results = [condition_matches(c, context) for c in conditions]
    if match == "any":
        return any(results)
    return all(results)


def _merge_list_restriction(current: set[str] | None, incoming: list | None, *, allow: bool) -> set[str] | None:
    if not incoming:
        return current
    incoming_set = {str(x) for x in incoming}
    if allow:
        if current is None:
            return incoming_set
        return current & incoming_set
    return None


def apply_list_rules(rules: dict, restrictions: GovernanceRestrictions) -> None:
    if rules.get("allowed_models"):
        merged = _merge_list_restriction(restrictions.allowed_models, rules["allowed_models"], allow=True)
        restrictions.allowed_models = merged
    if rules.get("blocked_models"):
        restrictions.blocked_models.update(str(x) for x in rules["blocked_models"])
    if rules.get("allowed_providers"):
        restrictions.allowed_providers = _merge_list_restriction(
            restrictions.allowed_providers, rules["allowed_providers"], allow=True
        )
    if rules.get("blocked_providers"):
        restrictions.blocked_providers.update(str(x) for x in rules["blocked_providers"])
    if rules.get("allowed_provider_types"):
        restrictions.allowed_provider_types = _merge_list_restriction(
            restrictions.allowed_provider_types, rules["allowed_provider_types"], allow=True
        )
    if rules.get("blocked_provider_types"):
        restrictions.blocked_provider_types.update(str(x) for x in rules["blocked_provider_types"])
    if rules.get("blocked_capabilities"):
        restrictions.blocked_capabilities.update(str(x) for x in rules["blocked_capabilities"])
    if rules.get("local_only") is True:
        restrictions.local_only = True
    if rules.get("cloud_allowed") is False:
        restrictions.cloud_allowed = False


def _api_key_applies(rules: dict, context: dict[str, Any]) -> bool:
    ids = rules.get("api_key_ids")
    if not ids:
        return True
    current = str(context.get("api_key_id") or "")
    return current in {str(x) for x in ids}


def evaluate_policies(policies: list[PolicyRecord], context: dict[str, Any]) -> EngineDecision:
    """Evaluate policies and return a structured decision."""
    active = [p for p in policies if p.status == PolicyStatus.ACTIVE]
    active.sort(key=lambda p: (p.priority, p.name))

    matched: list[MatchedPolicy] = []
    restrictions = GovernanceRestrictions()
    org_action = PolicyAction.ALLOW
    key_action = PolicyAction.ALLOW
    org_denied = False

    for policy in active:
        rules = policy.rules or {}
        if policy.policy_type == PolicyType.API_KEY and not _api_key_applies(rules, context):
            continue

        applies = rules_match(rules, context)
        if not applies:
            continue

        apply_list_rules(rules, restrictions)

        action = policy.action
        reason = f"Policy '{policy.name}' matched ({policy.policy_type})"
        matched.append(
            MatchedPolicy(
                policy_id=policy.id,
                name=policy.name,
                policy_type=policy.policy_type,
                action=action,
                reason=reason,
                priority=policy.priority,
                version=policy.version,
            )
        )

        if policy.policy_type == PolicyType.API_KEY:
            if SEVERITY.get(action, 0) > SEVERITY.get(key_action, 0):
                key_action = action
        else:
            if SEVERITY.get(action, 0) > SEVERITY.get(org_action, 0):
                org_action = action
            if action == PolicyAction.DENY:
                org_denied = True

    if org_denied:
        final = PolicyAction.DENY
        reason = "Organization DENY overrides other actions"
    elif SEVERITY.get(org_action, 0) >= SEVERITY.get(key_action, 0):
        final = org_action
        reason = "Organization policy action selected"
    else:
        final = key_action
        reason = "API key policy action selected"

    if not matched:
        reason = "No matching policies — default ALLOW"

    if matched:
        chosen = max(matched, key=lambda m: SEVERITY.get(m.action, 0))
        if final == chosen.action:
            reason = chosen.reason

    return EngineDecision(
        action=final,
        reason=reason,
        matched=matched,
        restrictions=restrictions,
        org_denied=org_denied,
    )


def candidate_allowed(
    *,
    model_id: str,
    provider_name: str,
    provider_type: str,
    is_local: bool,
    restrictions: GovernanceRestrictions,
) -> tuple[bool, str | None]:
    if model_id in restrictions.blocked_models:
        return False, f"Model '{model_id}' is blocklisted"
    if restrictions.allowed_models is not None and model_id not in restrictions.allowed_models:
        return False, f"Model '{model_id}' is not on the allowlist"
    if provider_name in restrictions.blocked_providers or provider_type in restrictions.blocked_providers:
        return False, f"Provider '{provider_name}' is blocklisted"
    if provider_type in restrictions.blocked_provider_types:
        return False, f"Provider type '{provider_type}' is blocklisted"
    if restrictions.allowed_providers is not None and (
        provider_name not in restrictions.allowed_providers
        and provider_type not in restrictions.allowed_providers
    ):
        return False, f"Provider '{provider_name}' is not allowed"
    if restrictions.allowed_provider_types is not None and provider_type not in restrictions.allowed_provider_types:
        return False, f"Provider type '{provider_type}' is not allowed"
    if restrictions.local_only and not is_local:
        return False, "Policy requires local processing"
    if not restrictions.cloud_allowed and not is_local:
        return False, "Cloud providers are not allowed"
    return True, None
