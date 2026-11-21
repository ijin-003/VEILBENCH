# VEILBENCH update change log — 2026-11-21

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
