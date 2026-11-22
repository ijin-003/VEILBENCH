#!/usr/bin/env bash
# Destructive PostgreSQL restore. Requires an explicit confirmation environment variable.
set -Eeuo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"
BACKUP_FILE="${1:-}"
if [[ -z "$BACKUP_FILE" || ! -f "$BACKUP_FILE" ]]; then
  echo "Usage: sudo env CONFIRM_RESTORE=YES bash scripts/restore_postgres.sh /path/to/backup.dump" >&2
  exit 2
fi
if [[ "${CONFIRM_RESTORE:-}" != "YES" ]]; then
  echo "Refusing destructive restore. Set CONFIRM_RESTORE=YES after verifying the backup." >&2
  exit 1
fi
if [[ ! -f .env.production ]]; then
  echo "Missing .env.production" >&2
  exit 1
fi
docker compose --env-file .env.production -f docker-compose.production.yml exec -T veilbench-db \
  pg_restore --list < "$BACKUP_FILE" >/dev/null
docker compose --env-file .env.production -f docker-compose.production.yml exec -T veilbench-db \
  sh -c 'pg_restore --clean --if-exists --no-owner --single-transaction --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"' \
  < "$BACKUP_FILE"
echo "PostgreSQL restore completed from $BACKUP_FILE"
