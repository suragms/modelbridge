"""ARQ worker settings."""

from arq import cron
from arq.connections import RedisSettings

from app.config import get_settings
from app.jobs.agent_tasks import execute_agent_job, execute_workflow_job, run_scheduled_workflows
from app.jobs.intelligence_tasks import run_intelligence_analysis
from app.jobs.tasks import data_retention_cleanup, provider_health_checks
from app.jobs.webhook_tasks import deliver_webhook_job, process_webhook_retries

settings = get_settings()
interval = max(1, settings.health_check_interval_minutes)
health_minutes = set(range(0, 60, interval))


class WorkerSettings:
    functions = [
        provider_health_checks,
        data_retention_cleanup,
        execute_agent_job,
        execute_workflow_job,
        run_scheduled_workflows,
        run_intelligence_analysis,
        deliver_webhook_job,
        process_webhook_retries,
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 600
    cron_jobs = [
        cron(provider_health_checks, minute=health_minutes),
        cron(data_retention_cleanup, hour=settings.retention_job_hour_utc, minute=0),
        cron(run_scheduled_workflows, minute={0, 15, 30, 45}),
        cron(run_intelligence_analysis, hour={4}, minute=0),
        cron(process_webhook_retries, minute={1, 16, 31, 46}),
    ]
