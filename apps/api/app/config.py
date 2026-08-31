from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://modelbridge:modelbridge@localhost:5432/modelbridge"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Authentication
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440

    # Encryption
    encryption_key: str = ""

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000"]
    environment: str = "development"

    # Rate limiting defaults (org settings override per org)
    rate_limit_per_minute: int = 100
    rate_limit_per_day: int = 10000

    # Request limits
    max_request_body_bytes: int = 10 * 1024 * 1024  # 10 MB
    max_message_chars: int = 200_000
    max_tools_json_bytes: int = 256 * 1024
    max_embedding_inputs: int = 2048
    max_embedding_batch_chars: int = 1_000_000

    # Timeouts (seconds)
    gateway_timeout_seconds: float = 120.0
    provider_timeout_seconds: float = 90.0
    streaming_timeout_seconds: float = 300.0

    # Provider API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""

    # Ollama
    ollama_base_url: str = "http://localhost:11434"

    # Logging
    log_level: str = "INFO"
    log_prompts: bool = False

    # Data retention (days) — enforced by background worker
    request_log_retention_days: int = 30
    analytics_retention_days: int = 90
    audit_log_retention_days: int = 180

    # Background jobs
    health_check_interval_minutes: int = 5
    retention_job_hour_utc: int = 3

    # Response cache (Redis)
    cache_enabled: bool = True
    cache_key_prefix: str = "mb:cache"
    chat_cache_ttl_seconds: int = 3600
    embedding_cache_ttl_seconds: int = 86400
    semantic_cache_enabled: bool = False

    # Cloud deployment
    deployment_region: str = "local"
    plane_type: str = "unified"
    service_discovery_mode: str = "registry"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate_production_settings() -> list[str]:
    """Return list of configuration errors for production startup."""
    settings = get_settings()
    errors: list[str] = []
    if settings.environment == "production":
        if settings.jwt_secret in ("", "change-me-in-production", "test-secret"):
            errors.append("JWT_SECRET must be set to a secure value in production")
        if not settings.encryption_key:
            errors.append("ENCRYPTION_KEY is required in production")
        if not settings.database_url:
            errors.append("DATABASE_URL is required")
        if "*" in settings.cors_origins:
            errors.append("CORS origins must not include '*' in production")
    if not settings.database_url:
        errors.append("DATABASE_URL is required")
    return errors
