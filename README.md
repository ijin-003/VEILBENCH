> **Fast $0 academic deployment:** See [Zero-Budget Deployment](docs/ZERO_BUDGET_DEPLOYMENT.md) for Vercel Free + one Render Free web service + Neon Free PostgreSQL, with account login and real MPyC processes. This is a shared-host proof of concept, **not independent-operator privacy**.

# VEILBENCH

VEILBENCH is an academic three-founder salary-benchmark demo. Three isolated
MPyC parties compute a public sum and average with a fixed $(m=3,t=1)$ Shamir
MPC protocol. The coordinator stores only session metadata and the aggregate;
it has no salary-submission endpoint.

## What this revision implements

- A founder submits one salary directly to their designated party using a
  short-lived, session- and party-scoped capability. The browser calls the
  party's HTTPS endpoint; it does not send the value through the coordinator.
- The FastAPI coordinator creates metadata-only PostgreSQL sessions, polls
  party submission state, triggers all three MPyC parties, and saves only the
  agreed public aggregate and average.
- The Compose topology enables MPyC's own mutually authenticated TLS peer
  sockets (`--ssl`) and HTTPS for party endpoints. Credentials have no
  source-code defaults and are loaded from an untracked `.env` file.
- Each party persists only a non-sensitive SQLite replay guard on its own
  volume. Expired private input memory is purged automatically; interrupted
  computations retain a fail-closed coordinator barrier until party cleanup
  is confirmed.
- The Next.js UI provides a management page plus separate founder submission
  pages. Capability tokens are displayed once and kept only in browser memory.

## Trust boundaries

```
Founder browser -- HTTPS + scoped capability --> assigned MPC party
Coordinator   -- HTTPS + control token -----> all three MPC parties
MPC party     -- MPyC mTLS ----------------> other MPC parties
Coordinator   -- PostgreSQL ----------------> session metadata + aggregate only
```

Private salaries and MPyC shares must not be logged or persisted. The included
single-host Compose layout is a local demonstration, not independent
organization hosting. MPyC peer sockets use mTLS. The local development Compose
profile uses HTTPS plus bearer control credentials; the production Compose
profile additionally requires CA-signed client certificates on backend and
party HTTPS listeners. Caddy presents a dedicated edge certificate, while the
coordinator presents its own client certificate to parties. Read
`docs/PHASE_4_DEPLOYMENT.md` and `docs/PHASE_5_DEPLOYMENT_HARDENING.md` before
treating the project as deployment-ready.

## Quick start on Windows

Use the exact PowerShell instructions in the delivery document. In brief:

1. Create `.venv`, install `backend/requirements.txt`, and run the lightweight tests.
2. Generate local development certificates.
3. Copy `.env.example` to `.env`, generate unique secrets, and fill it in.
4. Run `docker compose up --build` for the PostgreSQL + three-party integration check.

The public API health endpoint is `/api/v1/health`. Session management routes
are `/api/v1/sessions` and require `X-VEILBENCH-Admin-Token`; there is
intentionally no coordinator salary endpoint.

## Production preparation (academic deployment)

The production-like VPS stack is defined separately in `docker-compose.production.yml`.
It publishes only Caddy on ports 80/443, keeps PostgreSQL and party control/MPyC ports
private, runs the backend as a non-root user, and applies Alembic migrations before the
API starts. The frontend is deployed separately to Vercel.

See [Phase 3 Production Preparation](docs/PHASE_3_PRODUCTION_PREPARATION.md),
[Phase 4 Deployment Runbook](docs/PHASE_4_DEPLOYMENT.md),
[Phase 5 Deployment Hardening](docs/PHASE_5_DEPLOYMENT_HARDENING.md), and
[Phase 6 Docker and End-to-End Verification](docs/PHASE_6_DOCKER_AND_E2E.md) for VPS provisioning,
temporary HTTPS hostnames, environment generation, mTLS certificates, network isolation,
Vercel variables, migrations, backups, sequential image builds, and the synthetic end-to-end
MPC test. A live
VPS deployment and public browser/MPyC end-to-end test still require the project owner
to provision a VPS and link the Vercel project.

## Project layout

- `backend/api/sessions.py` — metadata-only coordinator API
- `backend/mpc/party_service.py` — direct party input, expiry cleanup, and MPyC process runner
- `backend/mpc/party_state_store.py` — per-party durable replay/tombstone metadata
- `backend/mpc/coordinator.py` — legacy local test harness only; never used by the web API
- `backend/mpc/protocol.py` — MPyC secure summation
- `backend/models/session.py` — PostgreSQL session/aggregate schema
- `backend/migrations/` — Alembic schema migrations for production databases
- `frontend/src/app/` — management and direct-party founder pages
- `scripts/generate_certs.py` — development CA and service/MPyC certificates
- `docs/PHASE_0_TO_4_DELIVERY.md` — original implementation setup, evidence, and limitations
- `docker-compose.production.yml` — VPS-only stack with Caddy as the sole public ingress
- `infrastructure/caddy/Caddyfile` — public API and founder-input route allowlists
- `docs/PHASE_3_PRODUCTION_PREPARATION.md` — production stack and release gates
- `docs/PHASE_5_DEPLOYMENT_HARDENING.md` — enforced internal mTLS and network segmentation

## Three-founder browser workflow

The coordinator creates three party-scoped invitations. Each founder opens their own page and
submits directly to Party 0, Party 1, or Party 2. The coordinator only polls submission metadata;
it does not receive or proxy salaries. The management dashboard automatically refreshes session
status and enables computation only after all three party services confirm receipt.

See [Phase 2 Founder Workflow](docs/PHASE_2_FOUNDER_WORKFLOW.md) for the complete browser flow,
required public URL/CORS configuration, and production deployment notes. The founder submission
URL and its one-time capability must be distributed separately; never put the capability in a URL.


## Frontend dependency security upgrade

The frontend now targets Next.js 16.4.6, ESLint 10.15.0, React 19.3.1, and Node.js 22.13+ or 24.x.
See [the Next.js 16 dependency upgrade notes](frontend/DEPENDENCY_UPGRADE_NEXT16.md)
for the one-time lockfile refresh and verification commands. Do not run
`npm audit fix --force`.
