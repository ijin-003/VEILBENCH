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
  sockets (`--ssl`) and HTTPS for public party/control endpoints. Credentials
  have no source-code defaults and are loaded from an untracked `.env` file.
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
organization hosting. Read `docs/PHASE_0_TO_4_DELIVERY.md` before treating it
as a deployment guide.

## Quick start on Windows

Use the exact PowerShell instructions in the delivery document. In brief:

1. Create `.venv`, install `backend/requirements.txt`, and run the lightweight tests.
2. Generate local development certificates.
3. Copy `.env.example` to `.env`, generate unique secrets, and fill it in.
4. Run `docker compose up --build` for the PostgreSQL + three-party integration check.

The public API health endpoint is `/api/v1/health`. Session management routes
are `/api/v1/sessions` and require `X-VEILBENCH-Admin-Token`; there is
intentionally no coordinator salary endpoint.

## Project layout

- `backend/api/sessions.py` — metadata-only coordinator API
- `backend/mpc/party_service.py` — direct party input and MPyC process runner
- `backend/mpc/protocol.py` — MPyC secure summation
- `backend/models/session.py` — PostgreSQL session/aggregate schema
- `frontend/src/app/` — management and direct-party founder pages
- `scripts/generate_certs.py` — development CA and service/MPyC certificates
- `docs/PHASE_0_TO_4_DELIVERY.md` — setup, evidence, and limitations
