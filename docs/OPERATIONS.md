# Operations Runbook

Codex should update exact commands after implementation.

## Start

Expected final shape:

```bash
docker compose up -d
```

Then verify:

- web health
- API `/health`
- API `/ready`
- PostgreSQL health
- OCR readiness separately
- sync status

## Stop

```bash
docker compose down
```

Do not use `-v` during normal stop because that can remove database volumes.

## Update application

Expected safe sequence:

1. backup PostgreSQL
2. `git status`
3. pull reviewed code
4. build images
5. run migrations
6. restart services
7. health checks
8. smoke-test resume session and approval

## Database backup

Codex must add a script such as:

```text
scripts/backup-db.sh
```

Output backups outside the git repo or under ignored backup directory.

## Restore drill

Document:

- stopping writers
- creating/restoring DB
- migration compatibility
- validating counts
- reopening a known session

A backup is not considered trustworthy until restore is tested.

## Sync recovery

If Google Sheets is down:

- continue card approval
- inspect pending/error count later
- retry sync
- verify no duplicate Record IDs

## OCR recovery

If local OCR service is down:

- app remains available
- card can enter manual review
- operator can type final text
- optionally retry OCR later

Do not block all work because model inference is unavailable.

## Troubleshooting order

1. `docker compose ps`
2. application health endpoints
3. API logs
4. DB connectivity
5. OCR readiness
6. Tailscale connectivity
7. Google sync status

Avoid broad system changes before identifying failing component.
