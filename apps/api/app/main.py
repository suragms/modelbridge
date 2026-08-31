import time
import uuid
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text

from app.api.routes import (
    agents_router,
    analytics_router,
    api_keys_router,
    audit_router,
    auth_router,
    chat_router,
    embeddings_router,
    extensions_router,
    governance_router,
    logs_router,
    models_router,
    organizations_router,
    playground_router,
    providers_router,
    routing_router,
    workflows_router,
    templates_router,
    workspaces_router,
    projects_router,
    environments_router,
    enterprise_router,
    fleet_router,
    control_plane_router,
    cloud_router,
    usage_router,
    quotas_router,
    intelligence_router,
    operations_assistant_router,
    events_router,
    webhooks_router,
    integrations_router,
    automations_router,
    developer_router,
    marketplace_router,
    publishers_router,
    marketplace_admin_router,
    studio_router,
    prompts_router,
    evaluations_router,
    evaluation_runs_router,
)
from app.config import get_settings, validate_production_settings
from app.db.base import async_session_factory, engine
from app.services.extensions.registry import seed_official_packages
from app.services.extensions.tools import init_reference_tools
from app.services.metrics import metrics_response
from app.services.redis_client import close_redis

settings = get_settings()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    errors = validate_production_settings()
    if errors and settings.environment == "production":
        for err in errors:
            logger.error("config_validation_failed", error=err)
        raise RuntimeError("Invalid production configuration: " + "; ".join(errors))
    if errors:
        for err in errors:
            logger.warning("config_validation_warning", error=err)
    init_reference_tools()
    try:
        async with async_session_factory() as db:
            await seed_official_packages(db)
            from app.services.marketplace.seed import seed_marketplace_items

            await seed_marketplace_items(db)
            from app.services.cloud.regions import RegionService
            from app.services.cloud.discovery import ServiceDiscovery
            from app.config import get_settings

            await RegionService(db).seed_defaults()
            settings = get_settings()
            local_region = await RegionService(db).get_by_code(settings.deployment_region)
            if local_region:
                discovery = ServiceDiscovery(db)
                await discovery.register(
                    service_name="modelbridge-api",
                    region_id=local_region.id,
                    endpoint=await discovery.local_endpoint() or "http://localhost:8000",
                    plane_type=settings.plane_type,
                    capabilities=["chat", "embeddings", "agents", "workflows"],
                )
            await db.commit()
    except Exception as e:
        logger.warning("startup_seed_skipped", error=str(e))
    yield
    await close_redis()


app = FastAPI(
    title="ModelBridge",
    description="One API for every AI model. An open-source AI gateway and intelligent model router.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_and_limits_middleware(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH"}:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_request_body_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "type": "payload_too_large",
                        "message": f"Request body exceeds {settings.max_request_body_bytes} bytes",
                        "code": "PAYLOAD_TOO_LARGE",
                    }
                },
            )

    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    rate_headers = getattr(request.state, "rate_limit_headers", None)
    if rate_headers:
        for key, value in rate_headers.items():
            response.headers[key] = value

    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration, 2),
        request_id=request_id,
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "internal_error",
                "message": "An internal error occurred",
                "code": "INTERNAL_ERROR",
            }
        },
    )


app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(providers_router)
app.include_router(models_router)
app.include_router(chat_router)
app.include_router(embeddings_router)
app.include_router(playground_router)
app.include_router(api_keys_router)
app.include_router(logs_router)
app.include_router(analytics_router)
app.include_router(routing_router)
app.include_router(audit_router)
app.include_router(governance_router)
app.include_router(agents_router)
app.include_router(workflows_router)
app.include_router(extensions_router)
app.include_router(templates_router)
app.include_router(workspaces_router)
app.include_router(projects_router)
app.include_router(environments_router)
app.include_router(enterprise_router)
app.include_router(fleet_router)
app.include_router(control_plane_router)
app.include_router(cloud_router)
app.include_router(usage_router)
app.include_router(quotas_router)
app.include_router(intelligence_router)
app.include_router(operations_assistant_router)
app.include_router(events_router)
app.include_router(webhooks_router)
app.include_router(integrations_router)
app.include_router(automations_router)
app.include_router(developer_router)
app.include_router(marketplace_router)
app.include_router(publishers_router)
app.include_router(marketplace_admin_router)
app.include_router(studio_router)
app.include_router(prompts_router)
app.include_router(evaluations_router)
app.include_router(evaluation_runs_router)


async def _check_database() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _check_redis() -> bool:
    try:
        client = aioredis.from_url(settings.redis_url, socket_timeout=2)
        await client.ping()
        await client.aclose()
        return True
    except Exception:
        return False


@app.get("/health")
async def health():
    db_ok = await _check_database()
    redis_ok = await _check_redis()
    checks = {
        "database": "healthy" if db_ok else "unhealthy",
        "redis": "healthy" if redis_ok else "unhealthy",
    }
    if db_ok and redis_ok:
        status = "healthy"
    elif db_ok or redis_ok:
        status = "degraded"
    else:
        status = "unhealthy"
    return {"status": status, "version": "1.0.0", "checks": checks}


@app.get("/ready")
async def readiness():
    db_ok = await _check_database()
    redis_ok = await _check_redis()
    checks = {"database": "ok" if db_ok else "error", "redis": "ok" if redis_ok else "error"}
    if db_ok and redis_ok:
        return {"status": "ready", "checks": checks}
    return JSONResponse(status_code=503, content={"status": "not_ready", "checks": checks})


@app.get("/metrics")
async def prometheus_metrics():
    body, content_type = metrics_response()
    return Response(content=body, media_type=content_type)


@app.get("/")
async def root():
    return {
        "name": "ModelBridge",
        "version": "1.0.0",
        "description": "One API for every AI model.",
        "docs": "/docs",
        "metrics": "/metrics",
    }
