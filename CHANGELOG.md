## Phase 4.1.3 — ESLint 10 peer-conflict and health-effect correction

- Replaced the aggregate `eslint-config-next` dependency with the official
  `@next/eslint-plugin-next` direct plugin, React Hooks 7.1.1, TypeScript ESLint
  8.73.0, and `@eslint/js` 10.0.1. This avoids installing Next's bundled
  `eslint-plugin-import`, `eslint-plugin-jsx-a11y`, and `eslint-plugin-react`
  packages whose declared peer ranges still exclude ESLint 10.
- Kept ESLint 10.15.0, React/React DOM 19.3.1, Next.js 16.4.6, and PostCSS
  8.5.33.
- Refactored the home-page health check so the request helper is state-free;
  the mount effect updates state only from asynchronous Promise callbacks and
  aborts outstanding requests on unmount. Manual refresh remains event-driven.
- Updated frontend dependency-policy tests and toolchain documentation.
- The source ZIP did not contain `frontend/package-lock.json`; regenerate it
  after applying the manifest change, then run `npm ci` to verify it.
- No npm install, audit, ESLint, typecheck, or Next.js build is claimed in this
  environment because package registry access was unavailable. Those checks
  remain required on the user's machine.

# Changelog

## Phase 5 — deployment hardening and end-to-end readiness

- Enforced mTLS on production backend and party HTTPS listeners.
- Added a dedicated edge client certificate and Caddy upstream client authentication.
- Updated container health checks to authenticate with CA-signed client certificates.
- Added an internal mTLS smoke test to the VPS deployment workflow.
- Segmented the database network so the public edge cannot reach PostgreSQL.
- Added Phase 5 deployment verification and VPS sizing guidance.
- Added an idempotent environment migration that enables production mTLS without rotating existing secrets.
- Added real local Uvicorn mTLS integration checks for both the party and coordinator HTTPS listeners.

## Phase 4 — Deployment runbook and launch automation

- Added an Ubuntu VPS bootstrap script for Docker Engine and Compose, with opt-in UFW configuration.
- Added a production preflight validator for environment consistency, secret separation, certificate chain/hostname/expiry, and private-key permissions.
- Added a safe VPS deployment script that validates Compose and Caddy before starting services and runs read-only public smoke checks.
- Added public smoke tests for API readiness, party health, CORS, founder capability enforcement, and hidden party control routes.
- Added an explicitly confirmed PostgreSQL restore helper and a complete Vercel/VPS deployment runbook.
- Fixed production backend certificate mount directory creation.
- Restricted Caddy to the public CA certificate only and granted only `NET_BIND_SERVICE` after dropping other capabilities.
- Added a Vercel CLI ignore file to keep local environment files out of deployment uploads.

## Phase 4.1 — Frontend dependency security migration

- Upgraded the frontend manifest from Next.js 14.2 to Next.js 16.4.6 and
  updated `eslint-config-next` to 16.4.6 with ESLint 9.39.5.
- Pinned PostCSS to 8.5.33 and set Node.js 22.x as the frontend runtime.
- Replaced the removed `next lint` command with the ESLint CLI and migrated
  to Next.js 16's native flat ESLint configuration.
- Migrated the founder route to Promise-based App Router `params` while
  keeping React 18.3.1, which is supported by Next.js 16.
- Updated frontend Docker build/runtime stages to Node 22.
- The archive's existing lockfile still records the old dependency tree. Because
  package-registry access was unavailable during archive preparation, regenerate
  it with `npm install` in `frontend/` before running `npm ci` or Docker builds.
- No dependency audit clearance or frontend build success is claimed until
  the regenerated lockfile is installed and verified on the user's machine.

# VEILBENCH update change log — 2026-11-21

## Phase 3.1 — Windows test compatibility follow-up

- Marked the private-key POSIX mode-bit test as POSIX-only. Windows `chmod`
  does not implement POSIX group/other permission bits, so this test is skipped
  on Windows development machines. The production validator still enforces the
  `0o077` permission check on the intended Linux/POSIX deployment host.
- No runtime security behavior was weakened or changed.
- Verification in this build environment: `test_config.py` — 11 passed; all
  backend tests excluding `test_mpyc_protocol.py` — 95 passed, 2 skipped.
  MPyC integration tests could not run here because MPyC is not installed in
  this build environment; run them in the project's Windows virtualenv.


## Source basis

The referenced `VEILBENCH_phase0-4_updated.zip` and original Prompt 0–4 files
were not available in this workspace. This update therefore starts from the
only accessible staged VEILBENCH source copy and should be compared with the
user's archive before replacing any newer work.

## Changes

- Follow-up: separate founder signing secrets for each party; generic validation
  errors avoid echoing private submitted values; unknown party sessions report waiting.
- PostgreSQL admission lock plus persistent computation barrier; completed
  results are idempotent and interrupted runs require stopped-cluster recovery.
- Validate result session/party identities and protocol parameters. Pin MPyC 0.11.
- Add privacy/lifecycle regressions and correct disconnected-party stdin test.

- Added a metadata-only PostgreSQL session model and coordinator session API.
- Removed the global party salary route; founders now submit directly to a
  party-specific session route with a short-lived signed capability.
- Separated founder capabilities from party control credentials and removed
  hard-coded passwords/tokens from Compose and example configuration.
- Wired HTTPS service configuration and MPyC `--ssl` peer configuration using
  correctly named certificate locations for MPyC 0.11.
- Added development certificate generation for MPyC peers, party control
  endpoints, backend HTTPS, and coordinator client identity.
- Replaced the health-only frontend with management and direct-party founder
  pages. Salary submission is browser-to-party, not browser-to-coordinator.
- Added tests for token scoping/tampering, coordinator API surface, direct
  party route behavior, and revised certificate output expectations.
- Added setup and limitation documentation in `docs/PHASE_0_TO_4_DELIVERY.md`.

## Checks completed here

- `python -m compileall -q backend scripts` — passed.
- `python -m ruff check backend scripts` — passed.
- Full backend suite — `58 passed, 4 skipped` (2026-11-21), including real
  three-process MPyC calculations and disconnect handling. Certificate tests
  skipped because the OpenSSL CLI is unavailable. Lifecycle locking tests use
  database mocks and do not establish live PostgreSQL concurrency guarantees.
- `npm run lint` and `npm run build` — passed.
- Docker Compose YAML parsed successfully.
- `npm ci` reported 6 upstream dependency advisories (1 critical); no automatic
  audit upgrade was applied because it could change the locked application
  dependency set and needs separate review.

## Checks not completed here

- Local network tests passed with explicit execution permission. Docker is
  not installed here.
- No live PostgreSQL, Docker Compose, browser CORS, certificate-trust, HTTPS,
  or three-node mTLS integration test was performed. See the delivery document
  for exact target-machine commands.


## Phase 1 backend stabilization — current uploaded snapshot

- Added a per-party SQLite replay guard. Founder capabilities are claimed
  atomically and cannot be replayed after shutdown or party process restart.
  The store contains only session IDs, state markers, submission flags, and
  expiry timestamps; it never stores salaries or MPyC shares.
- Added party-session expiry cleanup and persistent failure marking when a party
  restarts after accepting an input.
- Changed coordinator orchestration to wait for all three compute requests
  before cleanup, retry party shutdown, and retain a fail-closed recovery
  barrier if any party cannot confirm cleanup.
- Added an authenticated session recovery endpoint that releases the global
  computation barrier only after all three parties confirm shutdown, plus an
  OpenAPI regression confirming the route exists without exposing a salary API.
- Fixed both distributed-party and legacy test-runner subprocess timeout
  handling to kill/reap child processes and drain stdout/stderr pipes,
  addressing unclosed Windows Proactor pipe transports seen in local output.
- Added separate persistent Docker volumes for each party's replay metadata
  and a `.state/` location for the Windows party launcher.
- No PostgreSQL schema change was required; no database migration was added.

### Checks run for this stabilization batch

- `python -m compileall -q backend` — passed.
- `python -m pytest backend/tests --ignore=backend/tests/test_mpyc_protocol.py -q -rA` —
  70 passed, 2 skipped. The two skips are OpenSSL-unavailable-only tests.
- The real MPyC protocol integration test was not run in this environment
  because MPyC is not installed in the provided execution environment. It must
  be run in the project's Windows virtual environment before accepting this
  batch.
- Docker Compose parsing, frontend build, and live PostgreSQL/three-party TLS
  integration were not run in this environment.

## Phase 2 — Three-founder browser workflow

- Added automatic metadata-only session polling to the coordinator dashboard.
- Added per-founder copy controls for the submission URL and one-time capability; the
  capability remains out of the URL and is intended to be distributed separately.
- Improved founder submission validation, duplicate-submit UX, and confirmation that the
  assigned party accepted the input.
- Kept founder salary submission as a direct browser-to-party HTTPS request; the coordinator
  still exposes no salary submission route.
- Marked session-creation responses containing founder capabilities as non-cacheable.
- Added runtime validation for distinct public party endpoints and production HTTPS/CORS
  origin configuration.
- Documented the production/Vercel public environment variables and academic deployment
  trust limitation.


## Phase 3 — Production preparation

- Added a dedicated production Docker Compose topology with Caddy as the only public ingress.
- Restricted public party hostnames to founder-input and health routes; party control routes remain private.
- Added non-root backend and MPC party images and a standalone production Next.js image.
- Added production configuration validation, readiness/liveness endpoints, and disabled API docs in production.
- Added Alembic initial schema migration and disabled automatic `create_all` in production.
- Added production environment generation, certificate permission hardening, and PostgreSQL backup helpers.
- Added VPS/Vercel deployment instructions and explicit academic single-host trust limitations.
- No deployment, commit, or push was performed as part of this phase.
- Added fail-closed production startup validation for coordinator and each party, including exact HTTPS origins, unique high-entropy secrets, certificate presence, private-key permissions, and persistent party-state paths.
- Scoped production environment variables per container: each party receives only its own founder signing secret and control token; Caddy receives hostnames only; PostgreSQL receives only database credentials.
- Added bounded container log rotation and read-only root filesystems for the API, party, and edge containers.


## Phase 4.1.2 — Frontend toolchain and React Hooks lint correction

- Upgraded React and React DOM together to 19.3.1 and matching TypeScript definitions to 19.3.0.
- Upgraded ESLint to supported 10.15.0 and PostCSS to 8.5.33.
- Expanded the supported Node engine range to Node 22.13+ or Node 24.x, covering the user's Node 24.11.1 runtime and Node 22 Docker image.
- Removed the synchronous loading-state update from the health-check function called by the mount effect; manual refresh now sets loading state in the click handler. No lint rule was disabled.
- The previous package lock was intentionally excluded from this patch archive because it predates the user's successful npm install and zero-vulnerability audit. Preserve the user's local lockfile and refresh it with `npm install` after applying this update.
- React/ESLint dependency installation and full frontend checks must be rerun on the user's machine; no claim is made that this follow-up has already passed those checks.


## Phase 4.1.2 — Frontend toolchain and React Hooks lint correction

- Upgraded React and React DOM together to 19.3.1 and matching TypeScript definitions to 19.3.0.
- Upgraded ESLint to supported 10.15.0 and PostCSS to 8.5.33.
- Expanded the supported Node engine range to Node 22.13+ or Node 24.x, covering the user's Node 24.11.1 runtime and Node 22 Docker image.
- Removed the synchronous loading-state update from the health-check function called by the mount effect; manual refresh now sets loading state in the click handler. No lint rule was disabled.
- The package lockfile is intentionally omitted from this patch archive because it predates the user's successful npm install and zero-vulnerability audit. Preserve the user's local lockfile and refresh it with `npm install` after applying this update.
- React/ESLint dependency installation and full frontend checks must be rerun on the user's machine; this follow-up does not claim those checks have already passed.

## Phase 6 — Docker build and MPC end-to-end verification

- Added a sequential production image build helper to reduce peak memory use
  on the low-cost academic VPS and to leave the running stack untouched when a
  build fails.
- Updated VPS deployment to build images before service replacement and start
  the stack with `--no-build` after all images are ready.
- Added an explicit, opt-in public synthetic three-founder smoke test that
  submits directly to each assigned party, verifies readiness and computes
  the expected aggregate without printing salaries or capabilities.
- Added automated tests for invitation routing, coordinator privacy, explicit
  test confirmation, aggregate correctness, and sequential deployment order.
