"""Reproducible, synthetic-only 3-party MPyC latency benchmark for Phase C.

This runs the genuine local MPyC worker processes through MPCCoordinator.
It does not touch the hosted Render service, database, accounts, or credentials.
Recorded CPU/memory metrics describe the GitHub Actions runner, NOT Render Free.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import platform
import resource
import statistics
import sys
import time

from backend.mpc.coordinator import MPCCoordinator

# Use non-concurrent runs on distinct MPyC peer port ranges. Values are all
# synthetic and exercise different valid aggregates.
SCENARIOS = (
    (50000, 70000, 60000),
    (0, 90000, 120000),
    (120000, 150000, 180000),
    (40000, 50000, 60000),
    (51000, 72000, 63000),
    (80000, 90000, 100000),
    (100000, 200000, 300000),
)


def percentile(values: list[float], percentile: float) -> float:
    """Nearest-rank empirical percentile, suitable for a small sample."""
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]


async def measure(repeats: int, warmup: int, base_port: int) -> dict:
    if repeats < 1 or repeats > 20 or warmup < 0 or warmup > 3:
        raise ValueError("Use 1-20 measured runs and 0-3 warmups")
    if not 1024 <= base_port <= 65000 - (repeats + warmup + 1) * 10:
        raise ValueError("Invalid port range")

    coordinator = MPCCoordinator(timeout=45.0)
    seconds: list[float] = []
    cases: list[dict] = []
    for run_id in range(warmup + repeats):
        inputs = SCENARIOS[run_id % len(SCENARIOS)]
        expected_sum = sum(inputs)
        port = base_port + run_id * 10
        started = time.perf_counter()
        result = await coordinator.execute_protocol(inputs, custom_base_port=port)
        elapsed_ms = (time.perf_counter() - started) * 1000.0

        if result["aggregate_sum"] != expected_sum:
            raise AssertionError(f"Run {run_id}: incorrect aggregate")
        if result["average_salary"] != expected_sum / 3:
            raise AssertionError(f"Run {run_id}: incorrect mean")
        if len(result["party_results"]) != 3 or {
            part["party_id"] for part in result["party_results"]
        } != {0, 1, 2}:
            raise AssertionError(f"Run {run_id}: incorrect set of party results")
        if any(part["aggregate_sum"] != expected_sum for part in result["party_results"]):
            raise AssertionError(f"Run {run_id}: party result mismatch")

        if run_id >= warmup:
            seconds.append(elapsed_ms)
            cases.append({
                "run": run_id - warmup + 1,
                "elapsed_ms": round(elapsed_ms, 2),
                "aggregate_sum": expected_sum,
                "correct": True,
            })
        print(
            f"{'warmup' if run_id < warmup else 'measured'} "
            f"iteration {run_id + 1}/{warmup + repeats}: "
            f"{elapsed_ms:.1f} ms, correct, parties=3",
            flush=True,
        )

    child_peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    # On Linux ru_maxrss is KiB; it is the maximum peak of one reaped child,
    # not combined worker RSS, and should not be interpreted as Render usage.
    return {
        "benchmark": "VEILBENCH local 3-party MPyC subprocess secure summation",
        "environment": "GitHub Actions Linux runner",
        "utc_completed": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "measurement_scope": "MPCCoordinator spawning three local MPyC subprocesses; excludes live HTTP, browser and Neon",
        "warmup_runs": warmup,
        "measured_runs": repeats,
        "all_correct": True,
        "latency_ms": {
            "min": round(min(seconds), 2),
            "median": round(statistics.median(seconds), 2),
            "mean": round(statistics.mean(seconds), 2),
            "p95_nearest_rank": round(percentile(seconds, 0.95), 2),
            "max": round(max(seconds), 2),
        },
        "memory": {
            "maximum_single_child_peak_rss_kib": int(child_peak),
            "note": "Linux RUSAGE_CHILDREN maxrss is the maximum for any one child, not total concurrent party memory or Render memory",
        },
        "runs": cases,
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=6)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--base-port", type=int, default=14300)
    parser.add_argument("--output", default="artifacts/mpyc-benchmark.json")
    args = parser.parse_args()

    result = await measure(args.runs, args.warmup, args.base_port)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("\n=== MPyC latency summary (CI environment, NOT Render) ===")
    print(json.dumps(result["latency_ms"], indent=2))
    print("Maximum individual child-process RSS (KiB):", result["memory"]["maximum_single_child_peak_rss_kib"])
    print("Report:", str(path))


if __name__ == "__main__":
    if sys.platform != "linux":
        raise SystemExit("Benchmark resource units are defined for Linux only")
    asyncio.run(main())
