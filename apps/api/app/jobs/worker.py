"""ARQ worker settings."""

from arq import cron
from arq.connections import RedisSettings

from app.config import get_settings
from app.jobs.tasks import data_retention_cleanup, provider_health_checks

settings = get_settings()
interval = max(1, settings.health_check_interval_minutes)
health_minutes = set(range(0, 60, interval))


class WorkerSettings:
    functions = [provider_health_checks, data_retention_cleanup]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 600
    cron_jobs = [
        cron(provider_health_checks, minute=health_minutes),
        cron(data_retention_cleanup, hour=settings.retention_job_hour_utc, minute=0),
    ]
