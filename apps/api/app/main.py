import time
import uuid

import redis.asyncio as aioredis
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db.base import engine
from app.config import get_settings

from app.api.routes import (
    analytics_router,
    api_keys_router,
    auth_router,
    chat_router,
    logs_router,
    models_router,
    providers_router,
)

settings = get_settings()
logger = structlog.get_logger()

app = FastAPI(
    title="ModelBridge",
    description="One API for every AI model. An open-source AI gateway and intelligent model router.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start = time.time()

    response = await call_next(request)
    duration = (time.time() - start) * 1000

    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration, 2),
        request_id=request_id,
    )
    response.headers["X-Request-ID"] = request_id
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


# Include routers
app.include_router(auth_router)
app.include_router(providers_router)
app.include_router(models_router)
app.include_router(chat_router)
app.include_router(api_keys_router)
app.include_router(logs_router)
app.include_router(analytics_router)


async def _check_database() -> bool:
    """Return True if the database is reachable."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _check_redis() -> bool:
    """Return True if Redis is reachable."""
    try:
        client = aioredis.from_url(settings.redis_url, socket_timeout=2)
        await client.ping()
        await client.aclose()
        return True
    except Exception:
        return False


@app.get("/health")
async def health():
    """Liveness probe. Returns 200 when the process is running."""
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/ready")
async def readiness():
    """Readiness probe. Checks that critical dependencies are reachable.

    Returns 200 only when both the database and Redis are available.
    """
    db_ok = await _check_database()
    redis_ok = await _check_redis()

    checks = {
        "database": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
    }

    if db_ok and redis_ok:
        return {"status": "ready", "checks": checks}
    return JSONResponse(
        status_code=503,
        content={"status": "not_ready", "checks": checks},
    )


@app.get("/")
async def root():
    return {
        "name": "ModelBridge",
        "version": "0.1.0",
        "description": "One API for every AI model.",
        "docs": "/docs",
    }
