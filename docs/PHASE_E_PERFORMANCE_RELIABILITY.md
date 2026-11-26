# Phase E — Performance and Reliability Evaluation

**Project:** VEILBENCH, privacy-preserving three-founder salary benchmark  
**Assessment date:** 2026-11-23 (UTC)  
**Evidence classification:** archived CI data + passive hosted telemetry + isolated reliability tests  
**Status:** **local MPC performance baseline and fault-control evidence established; repeated hosted computation timings remain outstanding.**

## Executive summary

VEILBENCH's genuine 3-party MPyC protocol successfully computes sums and averages using synthetic salaries. Two completed CI benchmarks each used **one warmup plus six measured sequential runs** on separate GitHub Actions Linux runners. The prior median was **179.73 ms** (mean 181.21 ms); the fresh Phase E run median was **242.20 ms** (mean 239.53 ms). The largest single-child peak RSS was 29,932 KiB on the older run and 30,068 KiB on the new run. Variation across CI workers means neither result should be presented as a production speed guarantee. These values do **not** measure the Render-hosted system, browser latency, PostgreSQL/Neon or three combined party-process memory peaks.

For the hosted Render service, seven available **hourly memory telemetry points** on 2026-11-22 and 2026-11-23 ranged from **67.19 to 103.60 MiB**, with an arithmetic mean of **82.98 MiB across samples**. These points came from **different instances and hours** and are insufficient to estimate the peak memory consumption of a short-lived MPC computation. The same query returned no CPU, HTTP request-count or HTTP latency samples; these metrics are therefore **unavailable**, not zero.

Existing missing-party, cleanup, and restart tests provide evidence for fail-closed behavior; the Phase E CI extends the repeatable benchmark with specific cleanup and recovery regression tests and original JUnit outputs.

## 1. Experimental setup and raw evidence

| Evidence | Source | Time / environment |
|---|---|---|
| 6-run historical baseline with 1 warmup | GitHub Actions run [45075066668](https://github.com/ijin-003/VEILBENCH/actions/runs/45075066668) | 2026-11-22; Python 3.11 Linux CI worker; real 3-party local MPyC subprocesses |
| 6-run Phase E repetition with 1 warmup | [GitHub Actions run 45097787336](https://github.com/ijin-003/VEILBENCH/actions/runs/45097787336), artifact `veilbench-mpyc-phase-c-metrics` with JUnit reliability evidence | 2026-11-23; real local 3-party MPyC subprocesses; 8 recovery tests plus missing-party test passed |
| Memory telemetry | Connected Render metrics API, service `veilbench-poc-go1d` (`srv-dc1h06rl550s73efug7g`) | 2026-11-22 16:00–22:00 UTC, 2026-11-23 01:00 UTC; hourly points, multiple instance IDs |
| Hosted app status | Render deployment `dep-dc1mee942hec73aokjg0` reports live; frontend Vercel deployment READY | Status checked 2026-11-23 |
| Authenticated complete computation | CI [Phase D full-stack acceptance](https://github.com/ijin-003/VEILBENCH/actions/runs/45095940979) | 2026-11-23; temporary PostgreSQL, real local HTTP party services and actual MPyC subprocesses |
| Fault handling | Missing-party test `backend/tests/test_mpyc_protocol.py::test_disconnected_party_handling`, cleanup/restart and timeout tests listed in Phase E workflow | Synthetic, bounded laboratory checks |

**Metric types must not be conflated:** CI wall-clock computation includes local worker launch; the live API `Server-Timing: coordinator-compute;dur=...` includes coordinator status/compute/cleanup/DB finalization; a browser's Network timing also includes network and possible cold starts. These represent different experimental quantities.

### 1.1 Local MPyC compute timing

| Statistic | Earlier CI run, 2026-11-22 | Phase E CI run, 2026-11-23 |
|---|---:|---:|
| Warmup iterations | 1 | 1 |
| Measured iterations | 6 | 6 |
| Minimum | 175.84 ms | 222.18 ms |
| Median | 179.73 ms | 242.20 ms |
| Arithmetic mean | 181.21 ms | 239.53 ms |
| Nearest-rank p95 | 188.02 ms | 259.01 ms |
| Maximum | 188.02 ms | 259.01 ms |
| Correctness | All 6 measured computations validated | All 6 measured computations validated |
| Largest individual child peak RSS | 29,932 KiB | 30,068 KiB |

Nearest-rank p95 on just six values equals the largest observed value in each run and is **not** a reliable production p95 estimate; report it as a descriptive sample statistic only. The six samples do not establish scalable throughput, a service-level objective or statistical confidence bounds.

### 1.2 Render memory samples

The available metrics API reports the following bytes at the hourly timestamps. These are individual samples, not a continuous resource trace.

| UTC timestamp | Memory bytes | Approx MiB |
|---|---:|---:|
| 2026-11-22 16:00 | 70,455,300 | 67.19 |
| 2026-11-22 18:00 | 77,144,060 | 73.57 |
| 2026-11-22 19:00 | 76,627,970 | 73.08 |
| 2026-11-22 20:00 | 98,205,700 | 93.66 |
| 2026-11-22 21:00 | 98,779,140 | 94.20 |
| 2026-11-22 22:00 | 79,269,890 | 75.60 |
| 2026-11-23 01:00 | 108,630,020 | 103.60 |

Sample range **67.19–103.60 MiB**, sample mean **82.98 MiB**. The sparse observations do not prove application memory stability, characterize startup spikes or capture MPyC worker peaks. CPU usage, HTTP latency and request-count series returned **no data** for the queried interval.

## 2. Reliability and failure behavior

| Failure condition | Defense / expected behavior | Evidence level |
|---|---|---|
| Only 2 of 3 MPyC peers run | Protocol does not complete successfully within bounded observation interval; no aggregate released | Actual local fault-injection subprocess test |
| Party/control process hangs | Coordinator kills/reaps subprocesses after configured timeout | Unit test of process cleanup |
| Coordinator receives non-matching party results | Reject inconsistent result identities or aggregate sums instead of publishing | Coordinator regression tests |
| Party restart after one-time submission | Persistent replay guard disallows resubmission; incomplete volatile state marked failed | Local SQLite restart tests |
| Shutdown intermittently fails | Retry shutdown across parties; keep recovery barrier if cleanup not confirmed | Mock-transport integration tests |
| Operator recovery | Release coordinator global barrier only after all parties confirm shutdown | Session lifecycle service tests |
| Wrong/duplicate founder submission | Rejected; state cannot be reused to alter submitted input | Security regression tests |

**Do not claim automatic recovery or uninterrupted service.** A failed computation can invalidate its current session; operator recovery may be needed. Dedicated independent failure domains are not present in the single Render free-container deployment.

## 3. Remaining hosted measurement procedure

The one successful website demonstration confirmed the result, but no timestamped hosted compute durations were captured in this evidence set. To complete the hosting-specific performance comparison, collect **at least three separate synthetic sessions** in the administrator browser, during normal human-paced use and without load testing:

1. For each session, use the synthetic founder inputs 50,000 / 70,000 / 60,000 and verify 180,000 / 60,000.
2. In DevTools → Network, inspect only the successful `POST /api/v1/sessions/{session_id}/compute`. Record the numeric `Server-Timing: coordinator-compute;dur=<ms>` value and the request's browser elapsed time.
3. Record UTC time and whether the service was cold/warm; do not record Authorization, session IDs, invitation/capability tokens or individual input requests.
4. Review Render CPU and memory near each timestamp, if present; explicitly mark missing telemetry as unavailable.
5. Report min/median/mean/max based on the real hosted observations, clearly separate client HTTP elapsed duration from server computation.

**Do not run concurrent requests, stress-test, disconnect a production party, or use real salary information.** The demo runs three logical party processes under one Render host/operator and cannot satisfy multi-operator isolation claims.

| Hosted trial | Server-Timing (ms) | Browser elapsed (ms) | Cold / warm | Verified result |
|---|---:|---:|---|---|
| 1 | Not yet measured | Not yet measured | Unknown | Pending |
| 2 | Not yet measured | Not yet measured | Unknown | Pending |
| 3 | Not yet measured | Not yet measured | Unknown | Pending |

## 4. Acceptance criteria and assessment

- [x] Real local MPyC wall-time baseline measured with synthetic values.
- [x] Aggregate correctness verified across both sets of six local benchmark runs.
- [x] Local disconnected-party safety check previously passed.
- [x] Hosted memory observations collected with units and timestamps.
- [x] Authenticated three-party Phase D local full-stack success previously verified.
- [x] Phase E extended cleanup/restart CI: eight focused recovery tests passed; missing-party test passed. [Original workflow](https://github.com/ijin-003/VEILBENCH/actions/runs/45097787336).
- [ ] At least three **measured** hosted `Server-Timing` observations.
- [ ] At least three browser-observed computation request timings.
- [ ] Final hosted-to-local comparison with clear difference in measurement scope.

## 5. Interpretation for academic defense

**Supported conclusion:** VEILBENCH demonstrated correct three-party secure summation with local subprocess medians of 179.73 and 242.20 ms across two CI runs, protected against a missing participant by failing to finish rather than exposing partial aggregate data, and provided recovery/replay protections covered by regression tests. Memory telemetry confirms the hosted service emitted some observable resource samples, but *not* the memory used by a specific computation.

**Unsupported conclusion:** That the deployed application computes every benchmark in ~180–242 ms, stays under 104 MiB at all times, reaches 95% of requests within 188 ms, automatically recovers from node failures or tolerates one physically compromised independent MPC operator on the shared demo host.
