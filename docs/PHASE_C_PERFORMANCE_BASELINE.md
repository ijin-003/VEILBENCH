# Phase C — MPC performance and reliability baseline

**Status:** Baseline measured on GitHub Actions, 2026-11-22 (UTC). This is **not a hosted Render performance claim**.

## Objective and setup

Measure repeated real three-party Shamir-based secure summation using MPyC on synthetic inputs, and verify a required party being unavailable causes safe non-completion.

- Execution: Linux GitHub Actions runner, Python 3.11, installed backend dependencies.
- Runner: `python -m scripts.benchmark_mpyc_phase_c --runs 6 --warmup 1`.
- Each iteration: `MPCCoordinator.execute_protocol` starts **three independent local Python/MPyC subprocesses**, connects over local TCP, reconstructs **only the aggregate sum**, and verifies the same result from all three parties.
- Repeats: 1 warm-up (discarded) followed by 6 measured, sequential executions on separate peer port ranges.
- Latency scope: time to launch the three subprocesses, execute local MPC, return outputs, and finish the coordinator call. Excludes HTTP, user authentication, browser, Neon queries, Vercel/Render networking, and free-host cold starts.
- Values were synthetic; all six sums and averages matched expected results.

## Empirical measurements

| Metric | Result |
|---|---:|
| Successful measured executions | 6 / 6 |
| Minimum wall-clock latency | 214.24 ms |
| Median wall-clock latency | 215.19 ms |
| Mean wall-clock latency | 216.91 ms |
| p95 nearest-rank latency | 223.59 ms |
| Maximum wall-clock latency | 223.59 ms |
| Largest individual child-process peak RSS | 30,004 KiB (~29.3 MiB) |
| Disconnected-party safety test | Passed (one required party missing; no successful computation) |

The memory observation uses Linux `resource.getrusage(RUSAGE_CHILDREN).ru_maxrss`. It is the **maximum of individual reaped children**, not an aggregate memory measurement for three simultaneous parties, coordinator, database connections, or the Render container.

The p95 statistic on only six samples is the maximum observed value (nearest-rank). These are illustrative baseline observations, not statistically robust SLO estimates. Hardware, operating system scheduling, runtime versions and network locality will affect performance.

## Threat/failure trade-offs and reliability

The disconnected-party fault-injection regression starts only two of the three required workers and confirms that the computation does not finish successfully. This is a fail-closed outcome, **not** evidence that availability is maintained during a party failure.

Existing integration tests also cover private-input clearance after successful computation, expiry/replay guards, and coordinator cleanup/recovery rules. Those protections are not proof of persistence of private salary values across restart—in fact, the design deliberately clears them.

## Deployment-specific limitations

The public $0 proof-of-concept runs coordinator and all three parties in one Render Free container. Its MPyC peers use loopback traffic without independent-host TLS, so the shared operator is trusted. This architecture is suitable for **synthetic academic demonstration only**.

Render Free may spin down or restart; party private input is volatile and a restart invalidates incomplete computations. Resource measurements above **cannot** establish that three live MPyC workers will fit in Render Free's memory budget.

## Remaining Phase C evidence before final report

1. Obtain **live** end-to-end latency measurements for a fresh synthetic admin + three-founder workflow, ideally 3–5 non-disruptive runs at different times. Report median, range, and cold-start separately.
2. Capture Render RAM/CPU time-series while an authorized synthetic computation runs, including the peak and instance restarts. Do not mistake the idle memory baseline for active worker memory.
3. Verify Neon-backed aggregate persistence after a normal page refresh and after a carefully planned service restart. Do not restart during a real user's session.
4. Document how failures, partial submissions, and retry/recovery states are displayed in the UI. Existing CI failure checks are necessary but not sufficient for hosted recovery guarantees.
5. Repeat on target class-demo environment before presentation.

## Reproducibility and sources

- Runner: `scripts/benchmark_mpyc_phase_c.py`.
- Workflow: `.github/workflows/mpyc-performance.yml`.
- Benchmark evidence artifact: https://github.com/ijin-003/VEILBENCH/actions/runs/45074740568/artifacts/14774418407
- GitHub Actions run: https://github.com/ijin-003/VEILBENCH/actions/runs/45074740568
- Fault regression: `backend/tests/test_mpyc_protocol.py::test_disconnected_party_handling`.
