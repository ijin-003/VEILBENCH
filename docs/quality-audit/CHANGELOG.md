# VEILBENCH — Audit Changelog

## Frontend (`audit/frontend` from `main` @ `b595afc00ff1605644584159e12f9f4fcb7753cc`)
- `frontend/src/app/AuthGateway.tsx`: Removed `useEffect` calling `setState` synchronously (fixes `react-hooks/set-state-in-effect` ESLint error).
- `frontend/src/app/page.tsx`: Added `key={activate ? "activate" : "login"}` on `<AuthGateway>` so mode switches reset form-local state cleanly.
- `frontend/src/app/AdminDashboard.tsx`:
  - Fixed `isConnected` to accept `health.status === "healthy"` (matching `/health`).
  - Fixed `react-hooks/set-state-in-effect` ESLint error in drawer effect and initialized `clockMs` to `Date.now()`.
  - Added `directorySeqRef` to prevent out-of-order directory poll overwrites.
  - Displayed `CLOSED` instead of live countdowns for `completed` and `failed` sessions.
  - Added `display_name` to `AccountRecord` and Account Directory rendering.
  - Added `recoverSession()` and `RECOVER STUCK SESSION` button when `state === "computing"`.
- `frontend/src/app/AccountInvite.tsx`: Added optional `display_name` display when an invitation is issued or reissued.
- `docs/quality-audit/*`: Added audit deliverables.

## Backend (`audit/backend` from `zero-budget-deploy` @ `76a9448c68e4a5a75468f4e17d38b87911faa4af`)
- `backend/api/accounts.py`: Added explicit `party_id in (0, 1, 2)` guard in `/api/v1/accounts/assignment`.
- `alembic.ini`: Added `path_separator = os` to resolve Alembic `DeprecationWarning`.
- `backend/tests/test_mpyc_protocol.py`: Added parametrized genuine 3-party MPyC tests for `(0,0,0)`, `(100,200,300)`, `(1,2,4)`, and `(1000000,2000000,3000000)`.
- `backend/tests/test_audit_regressions.py`: Added comprehensive regression suite covering Phases B, C, D, F, G, and K (20-step E2E workflow).
- `docs/quality-audit/*`: Added audit deliverables.

## Migration & Compatibility Impact
- **Database Migrations**: None required (all existing migrations `0001`–`0004` preserved and verified).
- **Dependencies**: No `package.json`, `package-lock.json`, `requirements.txt`, or `requirements-prod.txt` changes.
- **API Compatibility**: Fully backward-compatible between `audit/frontend` and `audit/backend`.
