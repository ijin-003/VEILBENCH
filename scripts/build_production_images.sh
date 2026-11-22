#!/usr/bin/env bash
# Pull external runtime images and build VEILBENCH services one at a time.
# Sequential builds reduce peak memory use on a small academic VPS.
set -Eeuo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"
ENV_FILE="${1:-${VEILBENCH_ENV_FILE:-.env.production}}"
COMPOSE_FILE="docker-compose.production.yml"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "Docker Engine and Docker Compose are required." >&2
  exit 1
fi
docker info >/dev/null
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")
"${COMPOSE[@]}" config --quiet

printf '\nPulling PostgreSQL and Caddy runtime images...\n'
"${COMPOSE[@]}" pull veilbench-db veilbench-edge

for service in veilbench-backend veilbench-mpc-node0 veilbench-mpc-node1 veilbench-mpc-node2; do
  printf '\nBuilding %s (sequentially)...\n' "$service"
  "${COMPOSE[@]}" build --pull "$service"
done

printf '\nAll production images built successfully. No containers were started or replaced.\n'
