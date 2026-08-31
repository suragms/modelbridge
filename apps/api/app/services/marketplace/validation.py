"""Marketplace package validation and security review."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.marketplace import SecurityReviewStatus
from app.services.extensions.manifest import validate_manifest, is_compatible

MODELBRIDGE_VERSION = "1.0.0"

SECRET_PATTERNS = ("password", "secret", "api_key", "token", "credential")


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    security_status: str = SecurityReviewStatus.NOT_REVIEWED


def scan_for_secrets(manifest: dict) -> list[str]:
    """Detect potential embedded secrets in manifest JSON."""
    findings: list[str] = []

    def walk(obj, path: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                key_path = f"{path}.{k}" if path else k
                if any(p in k.lower() for p in SECRET_PATTERNS) and isinstance(v, str) and len(v) > 8:
                    findings.append(f"Possible secret at {key_path}")
                walk(v, key_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                walk(item, f"{path}[{i}]")

    walk(manifest)
    return findings


def validate_dependencies(manifest: dict) -> list[str]:
    deps = manifest.get("dependencies") or []
    if not isinstance(deps, list):
        return ["dependencies must be a list"]
    errors: list[str] = []
    for dep in deps:
        if not isinstance(dep, dict):
            errors.append("Each dependency must be an object")
            continue
        if not dep.get("name"):
            errors.append("Dependency missing name")
        if dep.get("version") and not isinstance(dep["version"], str):
            errors.append(f"Invalid version for dependency {dep.get('name')}")
    return errors


def run_validation_pipeline(manifest: dict) -> ValidationResult:
    result = validate_manifest(manifest)
    errors = list(result.errors)

    min_ver = manifest.get("minimum_modelbridge_version", "1.0.0")
    if not is_compatible(str(min_ver), MODELBRIDGE_VERSION):
        errors.append(f"Incompatible: requires ModelBridge {min_ver}")

    errors.extend(validate_dependencies(manifest))
    secret_findings = scan_for_secrets(manifest)
    if secret_findings:
        errors.extend(secret_findings)

    security_status = SecurityReviewStatus.NOT_REVIEWED
    if not errors:
        security_status = SecurityReviewStatus.AUTOMATED_PASSED
    elif secret_findings:
        security_status = SecurityReviewStatus.AUTOMATED_FAILED

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        security_status=security_status,
    )
