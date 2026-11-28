# VEILBENCH — Security Findings

## Summary
- **Critical / High**: 0
- **Medium**: 1 (Directory polling race condition in `AdminDashboard.tsx`)
- **Low**: 3 (Missing `party_id` guard in `/assignment`, committed `.vs` cache in `main`, `ruff` lint hygiene)
- **Informational**: Shared-host Render trust boundary, heuristic password meter disclaimer.

## Findings

### SEC-01 (Medium) — Directory Polling Race Condition in `AdminDashboard.tsx`
- **File**: `frontend/src/app/AdminDashboard.tsx` (lines 139–154)
- **Root Cause**: `refreshDirectories` had no request sequence or `AbortController` guard; rapid toggling between `ACTIVE` and `HISTORY` or pagination could allow an older response to overwrite newer state.
- **Implemented Fix**: Added `directorySeqRef` sequence check before updating `accountDirectory`, `sessionDirectory`, `directoryError`, and `directoryBusy`.

### SEC-02 (Low) — Missing Explicit `party_id` Range Guard in `/api/v1/accounts/assignment`
- **File**: `backend/api/accounts.py` (lines 206–209)
- **Root Cause**: `assignment()` indexed `settings.founder_secrets[party_id]` without checking `party_id in (0, 1, 2)` first (would raise 500 `TypeError` if a corrupted participant row had `party_id=None`).
- **Implemented Fix**: Added `if party_id not in (0, 1, 2): raise HTTPException(403, "Invalid founder slot")`.

### SEC-03 (Low) — Committed IDE Cache in `main`
- **File**: `frontend/src/app/.vs/`
- **Root Cause**: Visual Studio `.vs` cache files (`slnx.sqlite`, `.suo`) were committed to `main`.
- **Recommendation**: Remove `frontend/src/app/.vs/` from git tracking in a cleanup commit and add `.vs/` to `.gitignore`.

### SEC-04 (Informational) — Shared-Host Render Trust Boundary
- **Scope**: `backend/ops/free_host_app.py`, `scripts/start_free_host.py`
- **Detail**: All three logical MPC parties run in one Render container/process under a single hosting operator. Shamir secret sharing protects against coordinator-route exposure and cross-party capability misuse, but **not** against a malicious hosting administrator or container-level inspection. Suitable for synthetic academic demonstration only.
