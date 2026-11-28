# VEILBENCH — Deployment Readiness

## 1. Frontend Readiness (`audit/frontend` -> `main` on Vercel)
- **Root Directory**: `frontend`
- **Node.js**: `^22.13.0 || ^24.0.0` (verified on `v24.11.1`)
- **Build & Checks**: `npm ci`, `npm run lint`, `npm run typecheck`, `npm run build`, and `npm audit` all pass with 0 errors and 0 vulnerabilities.
- **Required Vercel Env Vars**: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_PARTY_0_URL`, `NEXT_PUBLIC_PARTY_1_URL`, `NEXT_PUBLIC_PARTY_2_URL` (public URLs only).

## 2. Backend Readiness (`audit/backend` -> `zero-budget-deploy` on Render)
- **Runtime**: `infrastructure/Dockerfile.free` (`python:3.11-slim`, non-root user `veilbench`, `CMD ["python", "-m", "scripts.start_free_host"]`).
- **Migrations**: `scripts/start_free_host.py` runs `alembic upgrade head` automatically on boot before `uvicorn` starts with `workers=1`.
- **Health Check**: `/health/ready` (configured in `render.yaml`).
- **Required Render Env Vars**: `DATABASE_URL` (Neon direct URL), `FRONTEND_PUBLIC_URL`, `VEILBENCH_INITIAL_ADMIN_USERNAME`, `VEILBENCH_INITIAL_ADMIN_PASSWORD` (plus Render-generated secrets in `render.yaml`).

## 3. Recommended Deployment Order
1. Merge and deploy `audit/backend` -> `zero-budget-deploy` (Render runs `alembic upgrade head` and boots).
2. Verify `https://<render-host>/health/ready` and `/party/{0,1,2}/health`.
3. Merge and deploy `audit/frontend` -> `main` (Vercel builds and deploys).
4. Smoke-test one synthetic 3-founder session end-to-end.

## 4. Rollback Considerations
- No destructive schema migrations were added; both `audit/backend` and `audit/frontend` can be rolled back independently to `76a9448c` and `b595afc0` via standard Git/Vercel/Render rollbacks.
