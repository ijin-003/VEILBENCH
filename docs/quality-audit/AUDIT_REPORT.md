# VEILBENCH — Comprehensive Quality, Security, Functional & Deployment Audit Report

## 1. Executive Summary

An exhaustive code, security, cryptographic, database, and build/test audit of **VEILBENCH** was conducted across both production branches:
- **Frontend (`main`)**: `b595afc00ff1605644584159e12f9f4fcb7753cc` (audit branch: `audit/frontend`)
- **Backend (`zero-budget-deploy`)**: `76a9448c68e4a5a75468f4e17d38b87911faa4af` (audit branch: `audit/backend`)

No critical or high-severity security vulnerabilities were found in the cryptographic protocol, authentication, or access-control layers. However, several **medium- and low-severity functional and code-quality defects** were identified and fixed:
1. **Frontend ESLint Failures (Medium)**: `eslint .` failed on `main` (`LINT_EXIT=1`) due to two `react-hooks/set-state-in-effect` violations in `AdminDashboard.tsx` and `AuthGateway.tsx`. Fixed cleanly; `eslint .`, `tsc --noEmit`, and `next build` all pass.
2. **Broken Coordinator Health Indicator (Medium)**: `AdminDashboard.tsx` checked `health?.status.toLowerCase() === "ok"`, whereas `backend/api/health.py` returns `"healthy"`, causing the UI to permanently show `LINK UNVERIFIED`. Fixed to accept `"healthy"` and `"ok"`.
3. **Misleading Countdown on Completed/Failed Sessions & Initial Clock Flash (Medium)**: `AdminDashboard.tsx` rendered live countdowns for `completed` and `failed` sessions and initialized `clockMs` to `0`. Fixed to show `CLOSED` for completed/failed sessions and initialize `clockMs` to `Date.now()`.
4. **Directory Polling Race Condition (Medium)**: `AdminDashboard.tsx` lacked a sequence guard in `refreshDirectories`, allowing slow responses to overwrite newer scope/page selections. Fixed with `directorySeqRef`.
5. **Missing Founder Display Name & Session Recovery UI (Low)**: `AdminDashboard.tsx` and `AccountInvite.tsx` omitted `display_name` in the Account Directory / Invite confirmation, and `AdminDashboard.tsx` lacked a UI trigger for `/sessions/{id}/recover` on stuck `computing` sessions. Both added.
6. **Backend Guard & Alembic Deprecation Warning (Low)**: Added explicit `party_id in (0, 1, 2)` guard in `backend/api/accounts.py` (`/assignment`) and `path_separator = os` in `alembic.ini`.

## 2. Architecture Assessment

- **Genuine 3-Party MPyC**: Verified in `backend/mpc/protocol.py`, `party_service.py`, and `distributed_coordinator.py`. Uses MPyC `SecInt(l=32)`, fixed `m=3`, `t=1`, local homomorphic summation, and subprocess isolation.
- **Zero-Budget Deployment Topology**: Vercel (Next.js) + Render Free (single Docker container mounting `/api/v1` and `/party/{0,1,2}`) + Neon Free (PostgreSQL).
- **Important Trust Boundary**: Because all three logical parties run inside one Render container/process under one hosting operator, VEILBENCH demonstrates genuine 3-party Shamir MPC mechanics and role separation, **not** independent organizational trust or confidentiality against the hosting operator.

## 3. Open Pull Requests Reviewed (Phase N)

- **PR #10 (`security/attack-demonstration-lab`)**, **PR #11 (`test/phase-d-full-acceptance`)**, **PR #12 (`perf/phase-e-evaluation`)**, **PR #15 (`docs/phase-f-academic-report`)**: All were branched prior to migrations `0003_account_created_at` and `0004_founder_display_name` and `test_admin_directories.py`; merging them directly would delete those migrations and tests. Valuable test vectors from PR #11 and Phase G were incorporated into `backend/tests/test_audit_regressions.py` and `backend/tests/test_mpyc_protocol.py`.

## 4. Release-Readiness Conclusion

**CONDITIONAL PASS / READY FOR PR REVIEW**: All 168 executed backend tests (with 3 environment-specific skips), `compileall`, frontend `eslint`, `tsc --noEmit`, `next build`, and `npm audit` (0 vulnerabilities) pass after all fixes. Remaining environment-unavailable checks (live PostgreSQL concurrency, Playwright headless browser, `pip-audit` due to PyPI connection reset, and hosted Render timing) are documented in `TEST_RESULTS.md`.
