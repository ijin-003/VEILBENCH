# Phase D — Full-stack acceptance evidence and remaining hosted check

## Automation scope

The test in `backend/tests/test_phase_d_e2e.py` covers the **real VEILBENCH coordinator API**, a disposable PostgreSQL 16 database, three independent local HTTP party services and three MPyC computation subprocesses. No real account, Render/Neon database, or external endpoint is used. It is intentionally opted out of the ordinary unit suite.

The test is enabled only when `VEILBENCH_E2E_LOCAL=1` and rejects database URLs that do not use loopback. It uses synthetic local credentials and inputs: Founder 0 = 50,000; Founder 1 = 70,000; Founder 2 = 60,000. The only correct released result is 180,000 / 60,000.

### Automated acceptance checklist

| Step | Expected observation |
|---|---|
| Administrator authentication | 200; administrator access token granted |
| Session creation | 201; state = created; account-authenticated admin does not receive founder capability secrets |
| Founder invitations | Exactly three separate party assignments, invitations 201 |
| Activation | Each activation 200; replaying invitation 400 |
| Founder authentication | Login 200; authenticated party assignment matches session |
| Direct private submission | Exactly one party per founder, accepted 200; no salary in response |
| Replay prevention | Second submission rejected 409 |
| RBAC | Founder attempts administrator session retrieval, rejected 403 |
| All submissions | GET session reports party IDs [0,1,2], state = ready |
| Real MPC execution | POST compute 200; real 3-party MPyC sum 180000, average 60000 |
| Performance observation | Successful coordinator response includes numeric Server-Timing |
| Result persistence | Fresh GET after completion returns the same aggregate, no private inputs |

### Test execution

CI: `.github/workflows/backend-security.yml` (full-stack-acceptance job) and `.github/workflows/phase-d-acceptance.yml`. The runner provisions its own disposable PostgreSQL service. Do **not** run against production.

To reproduce locally, provide a **new disposable local PostgreSQL database** and run:

```bash
python -m pip install -r backend/requirements.txt
export VEILBENCH_E2E_LOCAL=1
export VEILBENCH_E2E_DATABASE_URL='postgresql+asyncpg://synthetic:LOCAL_TEST_PASSWORD@127.0.0.1:5432/veilbench_e2e'
python -m pytest backend/tests/test_phase_d_e2e.py -v -s -o addopts='--asyncio-mode=auto'
```

### Separate required production acceptance

A successful CI test does not verify browser-specific behavior, Render cold starts, frontend authentication storage, actual Vercel-to-Render CORS, public-party endpoint routing, Neon persistence or active worker memory. These require *authorized disposable hosted accounts* and should be tested manually on the deployed website:

1. Sign in as the demo administrator; create a fresh session.
2. Generate three invitations; activate and sign in as three unique founders.
3. Enter only synthetic values 50k/70k/60k, and confirm each party is marked submitted.
4. Compute exactly once; verify 180000 and 60000 and the Server-Timing header.
5. Refresh the administrator result page; confirm the aggregate persists without individual values.
6. Check logout/expired states and sensible UI errors.
7. Record only redacted screenshots and timestamps. Never capture credentials or invitation tokens.

If CI has not executed the latest acceptance job, status remains **PENDING**, even if older backend regression jobs passed.

### Architecture caveat

The publicly deployed $0 demo places the coordinator and three logical parties in one shared Render host. Independent operator trust, isolated hardware and mutually authenticated inter-party TLS are not achieved. Use synthetic values only.
