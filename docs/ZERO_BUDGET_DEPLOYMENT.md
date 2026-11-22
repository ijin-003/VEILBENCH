# VEILBENCH: $0 proof-of-concept deployment

This is an **academic demonstration**, not a distributed-trust production service.

## Architecture

- **Vercel Hobby (free):** Next.js frontend (set project root to `frontend`).
- **Render Free:** exactly one Docker web service. Its single Python process mounts four ASGI apps: the coordinator on `/api/v1`, and three independently scoped party applications at `/party/0`, `/party/1`, `/party/2`. On compute, each party invokes a **real MPyC subprocess**; peer traffic uses loopback TCP ports 11365–11367. Render provides browser-facing HTTPS.
- **Neon Free:** one remote PostgreSQL database. Only session metadata, account authentication and final aggregate results are stored there.

**Limitations:** All three parties share one Render container, Python process and hosting operator. This demonstrates **separate user accounts and real three-party MPC**, *not* three independently trusted organizations or protection against a malicious cloud operator. Render Free may sleep after 15 minutes, restart without warning, and has an **ephemeral filesystem**. In-progress salary inputs will be lost on restart and such sessions must be restarted. The 512 MB RAM limit might be insufficient for simultaneous MPyC workers; verify actual compute on the deployed instance before the class demonstration.

The original `docker-compose.production.yml` / mTLS configuration remains available for later, but is **not used** by this $0 deployment. Public HTTPS is terminated by Render. The loopback HTTP links have no protection against the shared container operator and should not be used for confidential real salaries. Use **synthetic demo salaries only**.

## Deployment: do these in order

1. **Neon:** Create one project on the **Free** plan at https://console.neon.tech. Use the direct (non-pooled) PostgreSQL connection URL. Copy it into **Render's secret environment variable editor**, **never into GitHub or chat**. If the URL has `sslmode=require`, the startup script converts it to SQLAlchemy/asyncpg's `ssl=require` parameter and removes a `channel_binding` query option unsupported by this database driver. Never commit the URL.
2. **Render:** Push this source to your GitHub repository, then visit https://dashboard.render.com/blueprints and create a Blueprint deployment using `render.yaml` on the repository root. Make sure the instance is **Free**, not a paid instance. Render generates seven application secrets. In the Render dashboard provide the four non-generated environment variables listed below. Render's public URL will look like `https://veilbench-poc.onrender.com`; its exact URL is not known until creation.
3. **Vercel:** Import the same GitHub repository at https://vercel.com/new. Set **Root Directory: `frontend`**, Node 22, Hobby. Add public environment variables (below), then deploy. Vercel's URL will look like `https://veilbench-....vercel.app`.
4. **Link the origins:** In Render, set `FRONTEND_PUBLIC_URL` to the **exact** Vercel HTTPS origin and redeploy. In Vercel set the four `NEXT_PUBLIC_` variables to the **exact** Render origin and redeploy. They are build-time variables and must be set **before the final Vercel build**.
5. **Smoke test:** Open `https://<render-host>/health/ready` and all three `https://<render-host>/party/{0,1,2}/health`. Open the Vercel frontend; log in with your admin account, create a benchmark, issue three invitations, activate three participant accounts in separate browser profiles, submit synthetic salaries, click Compute, and verify total and average. Do not claim success until live MPyC computation succeeds.

### Render environment variables

| Key | Where to get value |
|---|---|
| `DATABASE_URL` | Private PostgreSQL URL copied from Neon |
| `FRONTEND_PUBLIC_URL` | Exact Vercel origin, e.g. `https://your-veilbench.vercel.app` |
| `VEILBENCH_INITIAL_ADMIN_USERNAME` | Your chosen lowercase admin login (min 3 chars, letters/numbers/underscore/dot/hyphen) |
| `VEILBENCH_INITIAL_ADMIN_PASSWORD` | Private strong password, 12–128 characters |

Render automatically generates unique secret values for `COORDINATOR_ADMIN_TOKEN`, `MPC_NODE0_TOKEN`, `MPC_NODE1_TOKEN`, `MPC_NODE2_TOKEN`, and `MPC_FOUNDER_TOKEN_SECRET_{0,1,2}` through `render.yaml`. Keep all of them private. **Never paste them in chat.** On the first boot, migrations run and the admin account is created once. Subsequent boots will not overwrite the admin's password. To change it later, use your authenticated backend/admin workflow or update the database securely.

### Vercel public build variables

| Key | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://<render-host>` |
| `NEXT_PUBLIC_PARTY_0_URL` | `https://<render-host>/party/0` |
| `NEXT_PUBLIC_PARTY_1_URL` | `https://<render-host>/party/1` |
| `NEXT_PUBLIC_PARTY_2_URL` | `https://<render-host>/party/2` |

Only the four **public** URLs belong in `NEXT_PUBLIC_`. Do not put database passwords, founder capabilities, admin tokens or MPyC secrets there. `FRONTEND_PUBLIC_URL` and all backend secrets belong in **Render**, not Vercel.

### Notes / failures

- Initial Render request can take a minute after spin-down. Do one practice run immediately before class.
- Render's disk is not persistent; post-restart private salary submissions cannot be recovered. Start a new session.
- A Render Free service runs in a constrained resource envelope. If it restarts during MPyC because of memory limits, do not claim this architecture passed a deployment test. On a strict $0 budget an alternative hosting plan must be evaluated before the live demo.
- The legacy operational `COORDINATOR_ADMIN_TOKEN` is retained internally for compatibility with existing tooling; students should use the admin *account* UI.
- Keep one ASGI worker. Multiple workers would create inconsistent per-party volatile session state.
- Account sessions are one-hour and stored in PostgreSQL; access tokens stay in browser memory. Salary values never go through the coordinator API route, but the shared Python process/operator remains trusted in this demo.
