#!/usr/bin/env bash
# Safe, repeatable deployment of the VEILBENCH academic VPS stack.
# It never removes named volumes and never prints environment secrets.
set -Eeuo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"
ENV_FILE="${VEILBENCH_ENV_FILE:-.env.production}"
COMPOSE_FILE="docker-compose.production.yml"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo: sudo bash scripts/deploy_vps.sh" >&2
  exit 1
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE. Generate it with scripts/generate_production_env.py first." >&2
  exit 1
fi
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "Docker Engine and the Docker Compose plugin are required. Run bootstrap_ubuntu_vps.sh first." >&2
  exit 1
fi
if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required for public readiness checks." >&2
  exit 1
fi

python3 scripts/validate_production_env.py --env-file "$ENV_FILE"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")
"${COMPOSE[@]}" config --quiet

# The Caddy image has ENTRYPOINT=caddy, so override it explicitly for validation.
"${COMPOSE[@]}" run --rm --no-deps --entrypoint caddy veilbench-edge \
  validate --config /etc/caddy/Caddyfile --adapter caddyfile

# Build sequentially before changing running containers. This limits peak memory
# use on the low-cost academic VPS and leaves the previous stack running if a
# Docker image build fails. The helper also pulls PostgreSQL and Caddy images.
VEILBENCH_ENV_FILE="$ENV_FILE" bash scripts/build_production_images.sh "$ENV_FILE"

# This operation preserves all named volumes (PostgreSQL, party tombstones, Caddy ACME state).
"${COMPOSE[@]}" up -d --no-build --remove-orphans

printf '\nVerifying authenticated and unauthenticated internal TLS behavior...\n'
"${COMPOSE[@]}" exec -T veilbench-backend python -m backend.ops.smoke_test_internal_mtls

API_HOST="$(sed -n 's/^VEILBENCH_API_HOST=//p' "$ENV_FILE" | tail -n 1)"
PARTY0_HOST="$(sed -n 's/^VEILBENCH_PARTY0_HOST=//p' "$ENV_FILE" | tail -n 1)"
PARTY1_HOST="$(sed -n 's/^VEILBENCH_PARTY1_HOST=//p' "$ENV_FILE" | tail -n 1)"
PARTY2_HOST="$(sed -n 's/^VEILBENCH_PARTY2_HOST=//p' "$ENV_FILE" | tail -n 1)"
FRONTEND_ORIGIN="$(sed -n 's/^FRONTEND_PUBLIC_URL=//p' "$ENV_FILE" | tail -n 1)"

printf '\nWaiting for public HTTPS readiness checks...\n'
python3 scripts/smoke_test_public.py \
  --api-url "https://${API_HOST}" \
  --party-0-url "https://${PARTY0_HOST}" \
  --party-1-url "https://${PARTY1_HOST}" \
  --party-2-url "https://${PARTY2_HOST}" \
  --frontend-origin "$FRONTEND_ORIGIN" \
  --retries 18 --retry-delay 5

printf '\nDeployment stack is running. Service status:\n'
"${COMPOSE[@]}" ps
printf '\nDo not announce completion until a real three-founder MPyC computation is tested in separate browsers.\n'
