# VEILBENCH — Test Execution Results

## Testing Environment
- **OS**: Windows (local developer workstation; no Docker)
- **Python**: `3.13.15` (isolated venv `veilbench-venv`)
- **Node.js / npm**: `v24.11.1` / `11.6.2`
- **Frontend Commit Base**: `b595afc00ff1605644584159e12f9f4fcb7753cc` (`audit/frontend`)
- **Backend Commit Base**: `76a9448c68e4a5a75468f4e17d38b87911faa4af` (`audit/backend`)

## Baseline Results (Before Fixes)
- **Frontend (`npm ci`)**: 235 packages installed, `npm audit`: 0 vulnerabilities across 267 dependencies.
- **Frontend (`npm run lint`)**: **FAILED** (`LINT_EXIT=1`) — 2 errors (`react-hooks/set-state-in-effect` in `AdminDashboard.tsx:158` and `AuthGateway.tsx:71`).
- **Frontend (`npm run typecheck`)**: PASSED (`TSC_EXIT=0`).
- **Frontend (`npm run build`)**: PASSED (`BUILD_EXIT=0`).
- **Backend (`python -m compileall -q backend`)**: PASSED (`COMPILEALL_EXIT=0`).
- **Backend (`ruff check backend`)**: **FAILED** (`RUFF_EXIT=1`) — 30 lint items (primarily `I001` import sorting, `B007`, `B008`, `E402`/`F811` in existing files).
- **Backend (`pytest backend/tests -v`)**: 156 passed, 6 skipped (5 OpenSSL CLI unavailable on default Windows PATH; 1 POSIX `chmod` check on Windows).

## Final Verification Results (After Fixes)
- **Frontend (`npm run lint`)**: **PASSED** (`LINT_EXIT=0`, 0 errors, 0 warnings).
- **Frontend (`npm run typecheck`)**: **PASSED** (`TSC_EXIT=0`).
- **Frontend (`npm run build`)**: **PASSED** (`BUILD_EXIT=0`, routes `/`, `/_not-found`, `/design-preview/operations`, `/submit/[sessionId]/[partyId]`).
- **Backend (`python -m compileall -q backend`)**: **PASSED** (`COMPILEALL_EXIT=0`).
- **Backend (`pytest backend/tests -v` with Git OpenSSL in PATH)**: **168 passed, 3 skipped** in 72.25s (`PYTEST_EXIT=0`).
  - Skipped:
    1. `backend/tests/test_certificates.py:88` (`Only runs when OpenSSL is NOT available`)
    2. `backend/tests/test_certificates.py:91` (`Only runs when OpenSSL is NOT available`)
    3. `backend/tests/test_config.py:208` (`POSIX chmod permission bits are enforced on the Linux production host, not Windows development hosts`)
  - Includes new audit regression tests in `backend/tests/test_audit_regressions.py` (Phases B, C, D, F, G, K) and `backend/tests/test_mpyc_protocol.py` (all 5 required synthetic MPyC vectors: `(50000,70000,60000)`, `(0,0,0)`, `(100,200,300)`, `(1,2,4)`, `(1000000,2000000,3000000)`).

## Local MPyC Performance Measurement (Phase L)
- 5 consecutive genuine 3-party MPyC runs (`[50000, 70000, 60000]` on Windows loopback ports `12400..12440`):
  - Durations (ms): `[1066.44, 845.74, 1340.37, 1434.14, 1358.24]`
  - Median: `1340.37 ms` (Min: `845.74 ms`, Max: `1434.14 ms`)

## Unavailable / Pending Checks
- **PostgreSQL native integration**: PostgreSQL 19 server binary (`pg_ctl`/`postgres`) was not available in `C:\Program Files\PostgreSQL\19\bin` for unprivileged local cluster startup; migration and E2E tests ran on disposable SQLite (`aiosqlite`), while `pg_advisory_xact_lock` behavior remains covered by existing mock/unit tests in `test_lifecycle.py` and `test_distributed.py`.
- **`pip-audit`**: PyPI connection reset (`ConnectionResetError 10054`) prevented installing `pip-audit` in the local environment.
- **Playwright Browser E2E**: `playwright` package was not installed in the project's `node_modules` or Python venv; UI logic was verified via TypeScript, ESLint, production Next.js build, and code inspection.
- **Hosted Render Timing**: Not executed (no authenticated hosted credentials provided; marked pending).
