# Zero-budget proof-of-concept verification

Verified 2026-11-22. This archive contains the Phase 6 source plus the existing
administrator/participant account implementation and its verification tests.

## Passed

- Frontend `npm run lint` and `npm run typecheck`: exit 0.
- Next.js 16.4.6 production build: `npm run build -- --webpack`, exit 0.
  The default Turbopack build is not the verified build mode on this Windows host.
- Full backend: 139 passed, 6 skipped, 2 Alembic deprecation warnings.
  Command: `python -m pytest backend/tests -o addopts="--asyncio-mode=auto" -q`.
- Alembic upgrade through `0002_accounts` and downgrade to `0001_initial`
  against a temporary SQLite database: passed; original benchmark table preserved.
- Account HTTP tests with real SQL storage: invitation activation, single-use
  invitations, password hashing, role restrictions, duplicate assignments,
  login expiry, logout revocation, and temporary lockout after failed logins.
- Three distinct participant logins obtained their own party-scoped capability,
  submitted 50000, 70000, and 60000 directly to three separate party application
  instances, and could not submit to another party or submit twice.
- Actual MPyC subprocesses computed total 180000 and average 60000 from those
  submissions; party services cleared private inputs afterward. HTTP requests
  in this integration test use ASGI transports; MPyC uses real local sockets.
- Existing 12 MPyC protocol tests remain part of the passing full suite.

## Exact limitations and remaining work

- Six skips: five checks require OpenSSL, one checks Linux-only file permissions.
- Two warnings: Alembic legacy path-separator configuration; no test failures.
- No standalone frontend unit-test/browser-test suite exists in this project.
  Lint, TypeScript, and production compilation are verified; interactive browser
  and deployed HTTPS end-to-end verification remain outstanding.
- PostgreSQL/Neon migration execution has not been verified by this run. SQLite
  migration success is not a claim of production PostgreSQL verification.
- Docker, Caddy and production mTLS runtime checks remain unverified on this host.
- Target budget is $0: Vercel Free frontend, Render Free backend, Neon Free
  PostgreSQL. No paid service or VPS is required or provisioned by this delivery.
- The compact single-service Render packaging has NOT been implemented or
  resource-tested. Existing Phase 6 multi-container/VPS files are retained as
  historical source, not instructions to purchase a VPS. Render routing, startup,
  restart recovery, free-tier resource fit, and hosted URLs remain to be completed.
- No live public deployment is claimed. Existing GitHub PR is not updated by
  merely downloading this ZIP; it contains local account changes beyond 71db1c9.

## Account demonstration

See `docs/ACCOUNT_DEMONSTRATION.md` for migration and administrator provisioning.
Each participant account belongs to one benchmark in this version. Create new
usernames for later sessions. Reset/reissue/reassignment workflows are not present.
Three accounts demonstrate access separation, not independent hosting ownership.

## Archive hygiene

Only source files and placeholder `.env.example` / `.env.local.example` templates
are included. Real environment files, private certificates, keys, databases,
state, Git metadata, node_modules, .venv, build outputs, and caches are excluded.
Synthetic test credentials are fixtures only, not real deployment credentials.
