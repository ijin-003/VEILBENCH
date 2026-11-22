#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_FILE="$BACKUP_DIR/veilbench-$STAMP.dump"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
umask 077
cd "$ROOT"
docker compose --env-file .env.production -f docker-compose.production.yml exec -T veilbench-db \
  sh -c 'pg_dump --format=custom --no-owner --username="$POSTGRES_USER" "$POSTGRES_DB"' \
  > "$BACKUP_FILE"
chmod 600 "$BACKUP_FILE"
echo "PostgreSQL backup created: $BACKUP_FILE"
