# VEILBENCH — Regression Checklist

| Phase / Requirement | Status | Evidence / Notes |
|---|---|---|
| Phase A: Repository inspection & baseline | PASS | Inspected `main` (`b595afc0`) & `zero-budget-deploy` (`76a9448c`), ran baseline suites |
| Phase B: Duplicate display names (same & cross session) | PASS | Verified in `test_phase_b_founder_identity_and_error_distinction` |
| Phase B: Spaces, case, Unicode, empty/control/length validation | PASS | Verified in `test_phase_b_founder_identity_and_error_distinction` |
| Phase B: Slot uniqueness & error distinction (401/404/409/422) | PASS | Verified in `test_phase_b_founder_identity_and_error_distinction` |
| Phase C: Password policy (12-char repeated, common, username, length) | PASS | Verified in `test_phase_c_d_password_policy_and_invitation_reissue` & `AuthGateway.tsx` |
| Phase C: Scrypt hashing, lockout, throttling, logout, RBAC | PASS | Verified in `test_accounts.py`, `test_http_security.py`, `test_audit_regressions.py` |
| Phase D: Invitation generation, reissue invalidation, `no-store` | PASS | Verified in `test_phase_c_d_password_policy_and_invitation_reissue` |
| Phase E: Session lifecycle, countdowns, completed/failed display, recovery | PASS | Fixed `AdminDashboard.tsx` countdowns & added recovery button; backend in `test_lifecycle.py` |
| Phase F: Alembic migrations (`0001`–`0004`) & legacy NULL preservation | PASS | Verified on SQLite in `test_phase_f_migration_preserves_legacy_accounts` |
| Phase F: Live PostgreSQL concurrency integration | BLOCKED | Local `postgres`/`pg_ctl` server binary unavailable in `Program Files\PostgreSQL\19\bin` |
| Phase G: Genuine 3-party MPyC (`50k/70k/60k`, `0/0/0`, `100/200/300`, `1/2/4`, `1M/2M/3M`, min/max) | PASS | Verified in `test_mpyc_protocol.py` & `test_phase_g_salary_domain_boundaries` |
| Phase H: Frontend lint, typecheck, production build, `npm audit` | PASS | `eslint .`, `tsc --noEmit`, `next build`, `npm audit` (0 vulns) all pass |
| Phase H: Playwright multi-viewport browser automation | BLOCKED | Playwright browser package not installed in project/venv |
| Phase I: Backend `compileall` & full `pytest` suite | PASS | `168 passed, 3 skipped` (`PYTEST_EXIT=0`) |
| Phase J: Python `pip-audit` dependency scan | BLOCKED | PyPI `ConnectionResetError 10054` during `pip install pip-audit` |
| Phase K: Full 20-step E2E workflow (coordinator + 3 parties + MPyC) | PASS | Verified in `test_phase_k_full_20_step_e2e_workflow` |
| Phase L: Local MPyC performance measurement | PASS | 5-run median `1340.37 ms` on Windows |
| Phase L: Hosted Render timing | NOT APPLICABLE | No authenticated hosted credentials provided; marked pending |
| Phase M & N: Deployment config & open PR (#10, #11, #12, #15) review | PASS | Verified `render.yaml`, `Dockerfile.free`, `next.config.js`, and PR branch diffs |
