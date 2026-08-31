"""Plugin manifest validation and semver compatibility."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.models.extension import PluginType

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")

VALID_PLUGIN_TYPES = {t.value for t in PluginType}

VALID_PERMISSIONS = frozenset({
    "ai_provider_access",
    "network_access",
    "tool_execution",
    "database_access",
    "webhook_access",
})

REQUIRED_MANIFEST_FIELDS = (
    "name",
    "display_name",
    "description",
    "version",
    "plugin_type",
    "author",
    "license",
    "minimum_modelbridge_version",
)


@dataclass
class ManifestValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    manifest: dict = field(default_factory=dict)


def parse_semver(version: str) -> tuple[int, int, int] | None:
    if not SEMVER_RE.match(version):
        return None
    parts = version.split("-")[0].split("+")[0].split(".")
    return int(parts[0]), int(parts[1]), int(parts[2])


def is_compatible(plugin_min: str, platform_version: str) -> bool:
    p = parse_semver(plugin_min)
    c = parse_semver(platform_version)
    if not p or not c:
        return False
    return c >= p


def validate_manifest(data: dict) -> ManifestValidationResult:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ManifestValidationResult(False, ["Manifest must be a JSON object"])

    for field_name in REQUIRED_MANIFEST_FIELDS:
        if field_name not in data or data[field_name] in (None, ""):
            errors.append(f"Missing required field: {field_name}")

    name = data.get("name")
    if name and not re.match(r"^[a-z][a-z0-9-]{1,98}[a-z0-9]$", str(name)):
        errors.append("Invalid name: use lowercase slug format")

    version = data.get("version")
    if version and not parse_semver(str(version)):
        errors.append(f"Invalid semver: {version}")

    plugin_type = data.get("plugin_type")
    if plugin_type and plugin_type not in VALID_PLUGIN_TYPES:
        errors.append(f"Invalid plugin_type: {plugin_type}")

    permissions = data.get("permissions") or []
    if not isinstance(permissions, list):
        errors.append("permissions must be a list")
    else:
        for perm in permissions:
            if perm not in VALID_PERMISSIONS:
                errors.append(f"Unknown permission: {perm}")

    if plugin_type in {PluginType.AGENT_TEMPLATE.value, PluginType.WORKFLOW_TEMPLATE.value}:
        if not data.get("template_definition") and not data.get("template"):
            errors.append("Template plugins require template_definition")

    if plugin_type == PluginType.TOOL.value:
        tool = data.get("tool") or {}
        if not tool.get("name") or not tool.get("input_schema"):
            errors.append("Tool plugins require tool.name and tool.input_schema")

    return ManifestValidationResult(len(errors) == 0, errors, data)
