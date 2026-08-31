"""Instantiate agent and workflow templates."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, AgentStatus, Workflow, WorkflowNode, WorkflowStatus
from app.models.extension import ExtensionInstallation, ExtensionPackageVersion, InstallationStatus, PluginType
from app.services.extensions.lifecycle import ExtensionLifecycleService


class TemplateInstallError(Exception):
    pass


def validate_template_params(schema: dict | None, params: dict) -> None:
    if not schema:
        return
    required = schema.get("required") or []
    props = schema.get("properties") or {}
    for field in required:
        if field not in params:
            raise TemplateInstallError(f"Missing required parameter: {field}")
    for key, value in params.items():
        if key not in props:
            continue
        expected = props[key].get("type")
        if expected == "string" and not isinstance(value, str):
            raise TemplateInstallError(f"Parameter {key} must be a string")
        if expected == "number" and not isinstance(value, (int, float)):
            raise TemplateInstallError(f"Parameter {key} must be a number")


async def install_agent_template(
    db: AsyncSession,
    org_id: uuid.UUID,
    version: ExtensionPackageVersion,
    params: dict,
    *,
    user_id: uuid.UUID | None,
    activate: bool = False,
) -> Agent:
    definition = version.template_definition or {}
    schema = definition.get("parameters_schema")
    validate_template_params(schema, params)

    system_prompt = definition.get("system_prompt", "")
    if params.get("topic"):
        system_prompt = f"{system_prompt}\n\nTopic: {params['topic']}"

    agent = Agent(
        organization_id=org_id,
        name=definition.get("name", version.package.display_name),
        description=version.package.description,
        status=AgentStatus.ACTIVE if activate else AgentStatus.DRAFT,
        system_prompt=system_prompt.strip(),
        model_configuration=definition.get("model_configuration", {}),
        tool_configuration=definition.get("tool_configuration", {}),
        memory_configuration=definition.get("memory_configuration", {}),
        max_steps=definition.get("max_steps", 10),
        timeout_seconds=definition.get("timeout_seconds", 300),
        created_by=user_id,
    )
    db.add(agent)
    await db.flush()
    return agent


async def install_workflow_template(
    db: AsyncSession,
    org_id: uuid.UUID,
    version: ExtensionPackageVersion,
    params: dict,
    *,
    user_id: uuid.UUID | None,
    activate: bool = False,
) -> Workflow:
    definition = version.template_definition or {}
    schema = definition.get("parameters_schema")
    validate_template_params(schema, params)

    workflow = Workflow(
        organization_id=org_id,
        name=definition.get("name", version.package.display_name),
        description=version.package.description,
        status=WorkflowStatus.ACTIVE if activate else WorkflowStatus.DRAFT,
        definition={"parameters": params},
        created_by=user_id,
    )
    db.add(workflow)
    await db.flush()

    for node in definition.get("nodes") or []:
        config = dict(node.get("config") or {})
        if params.get("review_message") and node.get("node_type") == "tool":
            config.setdefault("arguments", {})["message"] = params["review_message"]
        db.add(
            WorkflowNode(
                workflow_id=workflow.id,
                node_key=node["node_key"],
                node_type=node["node_type"],
                config=config,
                next_on_success=node.get("next_on_success"),
                next_on_failure=node.get("next_on_failure"),
                next_on_true=node.get("next_on_true"),
                next_on_false=node.get("next_on_false"),
            )
        )
    await db.flush()
    return workflow


async def install_template_from_installation(
    db: AsyncSession,
    installation: ExtensionInstallation,
    params: dict,
    *,
    user_id: uuid.UUID | None,
    activate: bool = False,
) -> Agent | Workflow:
    if installation.status != InstallationStatus.ENABLED:
        raise TemplateInstallError("Extension must be enabled before creating resources")

    version = installation.package_version
    if not version:
        raise TemplateInstallError("Package version not found")

    plugin_type = version.package.plugin_type
    if plugin_type == PluginType.AGENT_TEMPLATE.value:
        resource = await install_agent_template(db, installation.organization_id, version, params, user_id=user_id, activate=activate)
    elif plugin_type == PluginType.WORKFLOW_TEMPLATE.value:
        resource = await install_workflow_template(db, installation.organization_id, version, params, user_id=user_id, activate=activate)
    else:
        raise TemplateInstallError(f"Not a template extension: {plugin_type}")

    lifecycle = ExtensionLifecycleService(db)
    await lifecycle.record_execution(installation, success=True)
    return resource
