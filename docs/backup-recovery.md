# PostgreSQL Backup & Recovery

## Backup

```bash
# Custom format (recommended)
pg_dump -Fc -h $PGHOST -U $PGUSER -d modelbridge -f modelbridge-$(date +%Y%m%d).dump

# Plain SQL
pg_dump -h $PGHOST -U $PGUSER -d modelbridge > modelbridge.sql
```

## Restore

```bash
# From custom format
pg_restore -h $PGHOST -U $PGUSER -d modelbridge -c modelbridge-20260101.dump

# From SQL
psql -h $PGHOST -U $PGUSER -d modelbridge < modelbridge.sql
```

## After Restore

```bash
cd apps/api
alembic upgrade head
```

## Disaster Recovery Checklist

1. Restore PostgreSQL from latest backup
2. Restore Redis is optional (rate limit counters rebuild; job queue clears)
3. Run Alembic migrations
4. Verify `/health` and `/ready`
5. Restart API and worker pods/containers
6. Rotate secrets if compromise suspected

## What Is Not Backed Up Automatically

- Redis ephemeral data (rate limits, quota counters)
- Provider credentials (stored encrypted in PostgreSQL — included in DB backup)
- Docker volumes unless snapshotted at infrastructure level

Configure automated backups through your cloud provider or orchestration platform.
