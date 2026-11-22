# VEILBENCH Phase 5 — Deployment hardening and end-to-end readiness

## Scope

Phase 5 closes production deployment gaps discovered during the post-build review. It does not claim a live cloud deployment.

## Changes

1. Enforce mutual TLS on production backend and party HTTPS listeners using Uvicorn `--ssl-cert-reqs 2`.
2. Keep three distinct client identities: coordinator-to-party, edge-to-backend/party, and party-to-party MPyC certificates.
3. Generate a dedicated `edge/edge.crt` and `edge/edge.key`; the edge key is mounted only into Caddy.
4. Require Caddy to present its edge client certificate for every internal HTTPS upstream.
5. Update container health checks to present an authorized client certificate.
6. Add an internal smoke test that verifies the backend and each party accept the coordinator certificate and reject TLS clients without a certificate.
7. Separate PostgreSQL into a database-only internal network that Caddy does not join.
8. Keep public port publishing limited to TCP 80/443 and UDP 443.

## Apply to an existing VPS

This phase changes the internal certificate inventory. On an existing deployment, stop before rotating certificates or secrets. Back up `.env.production`, `infrastructure/certs`, PostgreSQL, and all named volumes. Run `python3 scripts/migrate_phase5_env.py .env.production` to add/enable only `MPC_REQUIRE_CLIENT_CERT=true` without changing any other secret. Generate the new edge certificate with the updated `scripts/generate_certs.py`, then run `scripts/secure_production_certs.sh` and `scripts/validate_production_env.py`. Do not use `--force` on the environment generator and do not run `docker compose down -v`.

For a fresh academic demo, follow `docs/PHASE_4_DEPLOYMENT.md` with the updated certificate generation and mTLS requirements.

## VPS sizing

For a single-host academic demonstration, plan for at least 2 vCPU, 4 GB RAM, and 40 GB SSD storage. A smaller VPS may start but can be unreliable during concurrent image builds or MPC runs. This is a practical recommendation, not a hard runtime minimum. Build images sequentially if memory is constrained.

## Verification gates

- Python backend regression suite passes.
- Certificate generation includes the edge client certificate.
- Production environment validator checks certificate chains, hostnames, key pairs, key purposes, ownership, and permissions.
- Compose YAML parses and production network membership is correct.
- Caddy configuration validates with the pinned Caddy image on the VPS.
- Docker images build on the target Linux host.
- Internal mTLS smoke test passes for the backend and all three parties.
- Public smoke tests pass through Caddy.
- A real three-founder run uses synthetic inputs and returns only the aggregate and average.
- PostgreSQL and party replay state survive a controlled restart.

Until the target VPS and Vercel deployment pass these gates, VEILBENCH remains deployment-prepared rather than publicly deployed.
