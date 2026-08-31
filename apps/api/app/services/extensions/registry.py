"""Extension registry: discover, search, publish."""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.extension import (
    ExtensionPackage,
    ExtensionPackageVersion,
    ExtensionPublisher,
    ExtensionRegistry,
    PluginType,
    TrustLevel,
)
from app.services.extensions.manifest import validate_manifest


class ExtensionRegistryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ensure_local_registry(self, org_id: uuid.UUID | None = None) -> ExtensionRegistry:
        q = select(ExtensionRegistry).where(
            ExtensionRegistry.registry_type == "local",
            ExtensionRegistry.organization_id == org_id,
        )
        result = await self.db.execute(q)
        reg = result.scalar_one_or_none()
        if reg:
            return reg
        reg = ExtensionRegistry(
            organization_id=org_id,
            name="Local Registry" if org_id else "Official Registry",
            registry_type="local",
            is_default=True,
        )
        self.db.add(reg)
        await self.db.flush()
        return reg

    async def search_packages(
        self,
        *,
        org_id: uuid.UUID | None = None,
        query: str | None = None,
        plugin_type: str | None = None,
        trust_level: str | None = None,
        category: str | None = None,
        publisher_slug: str | None = None,
        limit: int = 50,
    ) -> list[ExtensionPackage]:
        q = select(ExtensionPackage).join(
            ExtensionRegistry,
            ExtensionRegistry.id == ExtensionPackage.registry_id,
            isouter=True,
        )
        if org_id:
            q = q.where(
                or_(
                    ExtensionRegistry.organization_id.is_(None),
                    ExtensionRegistry.organization_id == org_id,
                )
            )
        else:
            q = q.where(ExtensionRegistry.organization_id.is_(None))

        if query:
            like = f"%{query}%"
            q = q.where(
                or_(
                    ExtensionPackage.name.ilike(like),
                    ExtensionPackage.display_name.ilike(like),
                    ExtensionPackage.description.ilike(like),
                )
            )
        if plugin_type:
            q = q.where(ExtensionPackage.plugin_type == plugin_type)
        if trust_level:
            q = q.where(ExtensionPackage.trust_level == trust_level)
        if category:
            q = q.where(ExtensionPackage.category == category)
        if publisher_slug:
            q = q.join(ExtensionPublisher, ExtensionPublisher.id == ExtensionPackage.publisher_id).where(
                ExtensionPublisher.slug == publisher_slug
            )
        q = q.order_by(ExtensionPackage.display_name).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().unique().all())

    async def publish_package(
        self,
        manifest: dict,
        *,
        registry_id: uuid.UUID | None,
        org_id: uuid.UUID | None,
        publisher_slug: str,
        publisher_name: str,
        trust_level: str = TrustLevel.COMMUNITY,
        category: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> ExtensionPackageVersion:
        validation = validate_manifest(manifest)
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))

        registry = await self.ensure_local_registry(org_id) if not registry_id else await self.db.get(
            ExtensionRegistry, registry_id
        )
        if not registry:
            raise ValueError("Registry not found")

        pub_result = await self.db.execute(
            select(ExtensionPublisher).where(ExtensionPublisher.slug == publisher_slug)
        )
        publisher = pub_result.scalar_one_or_none()
        if not publisher:
            publisher = ExtensionPublisher(
                organization_id=org_id,
                name=publisher_name,
                slug=publisher_slug,
                is_verified=trust_level == TrustLevel.VERIFIED,
            )
            self.db.add(publisher)
            await self.db.flush()

        pkg_result = await self.db.execute(
            select(ExtensionPackage).where(
                ExtensionPackage.registry_id == registry.id,
                ExtensionPackage.name == manifest["name"],
            )
        )
        package = pkg_result.scalar_one_or_none()
        if not package:
            package = ExtensionPackage(
                registry_id=registry.id,
                publisher_id=publisher.id,
                name=manifest["name"],
                display_name=manifest["display_name"],
                description=manifest.get("description"),
                plugin_type=manifest["plugin_type"],
                trust_level=trust_level,
                category=category or manifest.get("category"),
            )
            self.db.add(package)
            await self.db.flush()

        version_str = manifest["version"]
        ver_result = await self.db.execute(
            select(ExtensionPackageVersion).where(
                ExtensionPackageVersion.package_id == package.id,
                ExtensionPackageVersion.version == version_str,
            )
        )
        if ver_result.scalar_one_or_none():
            raise ValueError(f"Version {version_str} already published")

        template_def = manifest.get("template_definition") or manifest.get("template")
        version = ExtensionPackageVersion(
            package_id=package.id,
            version=version_str,
            compatibility_version=manifest.get("minimum_modelbridge_version", "1.0.0"),
            manifest=manifest,
            permissions=manifest.get("permissions") or [],
            configuration_schema=manifest.get("configuration_schema"),
            entry_point=manifest.get("entry_point"),
            template_definition=template_def,
            changelog=manifest.get("changelog"),
            published_by=user_id,
        )
        self.db.add(version)
        await self.db.flush()
        return version


async def seed_official_packages(db: AsyncSession) -> None:
    """Seed built-in official templates and reference packages."""
    svc = ExtensionRegistryService(db)
    registry = await svc.ensure_local_registry(None)

    existing = await db.execute(
        select(ExtensionPackage).where(
            ExtensionPackage.registry_id == registry.id,
            ExtensionPackage.name == "research-agent",
        )
    )
    if existing.scalar_one_or_none():
        return

    official_manifests = [
        {
            "name": "research-agent",
            "display_name": "Research Agent",
            "description": "Agent template for structured research tasks with echo and time tools.",
            "version": "1.0.0",
            "plugin_type": PluginType.AGENT_TEMPLATE.value,
            "author": "ModelBridge",
            "license": "Apache-2.0",
            "minimum_modelbridge_version": "1.0.0",
            "permissions": ["tool_execution", "ai_provider_access"],
            "trust_level": TrustLevel.OFFICIAL.value,
            "category": "research",
            "template_definition": {
                "name": "Research Agent",
                "system_prompt": "You are a research assistant. Summarize findings clearly.",
                "model_configuration": {"model": "auto", "execution_mode": "direct"},
                "tool_configuration": {"allowed_tools": ["echo", "current_time"]},
                "max_steps": 5,
                "timeout_seconds": 120,
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "Research topic"},
                    },
                    "required": ["topic"],
                },
            },
        },
        {
            "name": "approval-workflow",
            "display_name": "Approval Workflow",
            "description": "Workflow template with approval gate before terminal step.",
            "version": "1.0.0",
            "plugin_type": PluginType.WORKFLOW_TEMPLATE.value,
            "author": "ModelBridge",
            "license": "Apache-2.0",
            "minimum_modelbridge_version": "1.0.0",
            "permissions": ["tool_execution"],
            "trust_level": TrustLevel.OFFICIAL.value,
            "category": "approval",
            "template_definition": {
                "name": "Approval Workflow",
                "nodes": [
                    {"node_key": "start", "node_type": "start", "next_on_success": "tool1"},
                    {
                        "node_key": "tool1",
                        "node_type": "tool",
                        "config": {"tool_name": "echo", "arguments": {"message": "review"}},
                        "next_on_success": "approve",
                    },
                    {"node_key": "approve", "node_type": "approval", "next_on_success": "end"},
                    {"node_key": "end", "node_type": "terminal", "config": {"result": "approved"}},
                ],
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "review_message": {"type": "string"},
                    },
                },
            },
        },
        {
            "name": "hello-tool",
            "display_name": "Hello Tool Extension",
            "description": "Reference tool extension demonstrating manifest and permissions.",
            "version": "1.0.0",
            "plugin_type": PluginType.TOOL.value,
            "author": "ModelBridge",
            "license": "Apache-2.0",
            "minimum_modelbridge_version": "1.0.0",
            "permissions": ["tool_execution"],
            "trust_level": TrustLevel.OFFICIAL.value,
            "category": "utilities",
            "tool": {
                "name": "hello",
                "description": "Returns a greeting (reference extension)",
                "input_schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
                "risk_level": "low",
            },
            "entry_point": "modelbridge_hello_tool:HelloToolPlugin",
        },
    ]

    for manifest in official_manifests:
        trust = manifest.pop("trust_level", TrustLevel.OFFICIAL.value)
        await svc.publish_package(
            manifest,
            registry_id=registry.id,
            org_id=None,
            publisher_slug="modelbridge",
            publisher_name="ModelBridge",
            trust_level=trust,
            category=manifest.get("category"),
        )
