"""Studio import/export without secrets."""

from __future__ import annotations

import json
from typing import Any

SECRET_KEYS = frozenset({"password", "secret", "api_key", "token", "credential", "encrypted"})


def strip_secrets(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: "[REDACTED]" if any(s in k.lower() for s in SECRET_KEYS) else strip_secrets(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [strip_secrets(i) for i in obj]
    return obj


def export_resource(resource_type: str, data: dict) -> dict:
    return {
        "format": "modelbridge-studio-v1",
        "resource_type": resource_type,
        "data": strip_secrets(data),
    }


def validate_import(payload: dict) -> list[str]:
    errors: list[str] = []
    if payload.get("format") != "modelbridge-studio-v1":
        errors.append("Unsupported import format")
    if not payload.get("resource_type"):
        errors.append("Missing resource_type")
    if "data" not in payload:
        errors.append("Missing data")
    raw = json.dumps(payload.get("data") or {})
    if any(k in raw.lower() for k in ("whsec_", "sk-", "api_key")):
        errors.append("Import appears to contain secrets")
    return errors
