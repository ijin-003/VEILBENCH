# VEILBENCH — Evidence Register and Sign-off Matrix

**Purpose:** Prevent mixing actual test results, user observations, build status and outstanding measurements in the final academic submission.

| Requirement / assertion | Primary evidence | Observed status | Limit |
|---|---|---|---|
| Web frontend deployed | [Vercel project](https://veilbench.vercel.app), main SHA `8c82ffb` | Production deployment READY and homepage returned HTTP 200 at last verified checkpoint | Does not prove every authenticated interactive UI action |
| Updated account and session directory APIs live | Render `zero-budget-deploy` SHA `bb90e31`, deployment `dep-dc2039d6e07s73eio0rg` | Render marked Live after migration; backend CI green | Directory list requires authorized browser confirmation |
| Backend role/privacy regression | [Run 45099425007](https://github.com/ijin-003/VEILBENCH/actions/runs/45099425007) | **160 passed, 2 skipped** | Tests use disposable/local resources |
| Real three-party computation with account flow | [Run 45095940979](https://github.com/ijin-003/VEILBENCH/actions/runs/45095940979) | **1 integrated end-to-end acceptance passed** with temporary Postgres, three actual party apps and MPyC | CI is not the deployed cloud |
| Cryptographic correctness | `backend/mpc/protocol.py`, Phase D CI | Inputs 50k + 70k + 60k produced sum 180k, average 60k | Only the sum is reconstructed; the aggregate itself may leak cohort information |
| Security attack demonstration | [PR #10](https://github.com/ijin-003/VEILBENCH/pull/10), lab evidence artifact | Nine test scenarios passed in isolated CI | Not live penetration testing; not independent malicious-party security |
| Local MPC latency baseline | [Run 45075066668](https://github.com/ijin-003/VEILBENCH/actions/runs/45075066668) | 6 measured runs: **179.73 ms median**, 181.21 ms mean | Local CI subprocess time, not hosted timing |
| Repeated MPC/reliability evaluation | [Run 45097787336](https://github.com/ijin-003/VEILBENCH/actions/runs/45097787336), [PR #12](https://github.com/ijin-003/VEILBENCH/pull/12) | 6 measured runs: **242.20 ms median**; missing-party + eight targeted reliability checks passed | Runner-to-runner variance; not production memory or SLO |
| Shared-host privacy limitation | `backend/ops/free_host_app.py`, `docs/ZERO_BUDGET_DEPLOYMENT.md` | Explicit one-operator, one-host design | **Synthetic salary data only** |
| Live hosted salary result | User reported successful authorized live computation | Demonstrated by user prior to recent admin-directory release | No redacted screenshot or timing captured in evidence set |
| Updated admin feature visual acceptance | Admin session list/timer, account list, token copy, password check | **Pending** | Requires authorized browser verification |
| Hosted compute latency | Numeric server `Server-Timing` and browser Timing pane | **Pending three separate synthetic sessions** | Do not substitute CI medians |
| Final grading rubric alignment | Course-provided project specification and marking rubric | **Unverified** | Must review original course source before grading claims |

## Privacy-safe evidence capture procedure

For the university report, collect only the following:
- Redacted screenshot of the landing screen and admin reactor.
- Redacted Session Tools screenshots: active session timers and account status. Blur usernames if they refer to real people.
- A clean mock founder submission **receipt**, not a private salary form containing the value.
- Aggregated result view showing *only* the allowed total and mean.
- GitHub Actions job summary and the machine-readable CI JUnit/benchmark artifacts.
- For timing, only a numeric milliseconds value, the UTC timestamp and the category (cold/warm).

**Never include:** bearer tokens, invitation tokens, capability values, session IDs, credentials, database URL, account hashes, individual salary values or request bodies in the submitted report.

## Remaining sign-off steps

1. User confirms that the new administrator Account Directory and Session Directory appear, update and enforce appropriate role access.
2. User verifies the live password indicator and token-only clipboard with a **disposable account**.
3. User records (if feasible) three distinct hosted `coordinator-compute` durations using synthetic inputs.
4. Review institution's project guide/rubric, adapt headings, insert student/instructor details and source citations.
5. Review final deck and demonstrate with synthetic accounts. **Do not assert completed hosted timing while entries remain blank.**
