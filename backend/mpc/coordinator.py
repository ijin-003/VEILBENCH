"""MPC Session Coordinator. Orchestrates three distinct MPC party processes."""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional

from backend.mpc.config import DEFAULT_BASE_PORT, DEFAULT_PARTIES_COUNT, MPC_TIMEOUT_SECONDS
from backend.mpc.exceptions import (
    ConfigurationError,
    MPCTimeoutError,
    PartyDisconnectedError,
)
from backend.mpc.validation import validate_salary

logger = logging.getLogger("veilbench.mpc.coordinator")


class MPCCoordinator:
    """
    Coordinates asynchronous execution of 3 independent MPyC party processes.
    Ensures each party process receives only its own participant's input.
    """

    def __init__(
        self,
        parties_count: int = DEFAULT_PARTIES_COUNT,
        base_port: int = DEFAULT_BASE_PORT,
        timeout: float = MPC_TIMEOUT_SECONDS,
    ):
        if parties_count != 3:
            raise ConfigurationError(f"VEILBENCH protocol strictly requires 3 parties, got {parties_count}")

        self.parties_count = parties_count
        self.base_port = base_port
        self.timeout = timeout

    async def execute_protocol(
        self,
        salaries: List[int],
        custom_base_port: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute the 3-party MPC protocol with distinct processes.

        Args:
            salaries: List of 3 integers [salary_0, salary_1, salary_2].
            custom_base_port: Optional custom base port (useful for concurrent test isolation).

        Returns:
            Dict containing aggregate_sum, average_salary, and per-party execution status.
        """
        if len(salaries) != self.parties_count:
            raise ConfigurationError(
                f"Expected exactly {self.parties_count} inputs, got {len(salaries)}"
            )

        # Validate all inputs prior to protocol initiation
        validated_salaries = [validate_salary(s) for s in salaries]
        base_port = custom_base_port or self.base_port

        # Command to run party_runner module
        base_cmd = [
            sys.executable,
            "-m",
            "backend.mpc.party_runner",
        ]

        procs: List[asyncio.subprocess.Process] = []

        try:
            # Spawn each party process with ONLY its own salary input
            for i in range(self.parties_count):
                party_args = base_cmd + [
                    "-M",
                    str(self.parties_count),
                    "-I",
                    str(i),
                    "--base-port",
                    str(base_port),
                ]
                proc = await asyncio.create_subprocess_exec(
                    *party_args,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                procs.append(proc)

            # Wait for all 3 processes with timeout guard
            tasks = [
                process.communicate(json.dumps(salary).encode() + b"\n")
                for process, salary in zip(procs, validated_salaries, strict=True)
            ]
            done_outputs = await asyncio.wait_for(
                asyncio.gather(*tasks),
                timeout=self.timeout,
            )

        except asyncio.TimeoutError as e:
            # Clean up lingering child processes on timeout
            for p in procs:
                try:
                    p.kill()
                except ProcessLookupError:
                    pass
            raise MPCTimeoutError(
                f"MPC computation timed out after {self.timeout} seconds"
            ) from e

        # Parse outputs and verify exit codes
        party_results: List[Dict[str, Any]] = []

        for i, (stdout, stderr) in enumerate(done_outputs):
            proc = procs[i]
            out_str = stdout.decode("utf-8", errors="replace")
            err_str = stderr.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                # Extract error message if present
                error_msg = f"Party {i} exited with code {proc.returncode}"
                if "__MPC_ERROR_START__" in err_str:
                    try:
                        err_json_str = err_str.split("__MPC_ERROR_START__")[1].split("__MPC_ERROR_END__")[0]
                        err_obj = json.loads(err_json_str)
                        error_msg = f"Party {i} error: {err_obj.get('error', err_str)}"
                    except Exception:
                        error_msg = f"Party {i} stderr: {err_str}"
                elif err_str:
                    error_msg = f"Party {i} stderr: {err_str.strip()}"

                raise PartyDisconnectedError(error_msg)

            # Parse result from stdout
            if "__MPC_RESULT_START__" not in out_str:
                raise PartyDisconnectedError(
                    f"Party {i} completed without returning valid MPC protocol output markers"
                )

            res_json_str = out_str.split("__MPC_RESULT_START__")[1].split("__MPC_RESULT_END__")[0]
            party_result = json.loads(res_json_str)
            party_results.append(party_result)

        # Verify consensus across all parties
        sums = [r["aggregate_sum"] for r in party_results]
        averages = [r["average_salary"] for r in party_results]

        if not (sums[0] == sums[1] == sums[2]):
            raise ConfigurationError(
                f"Consensus failure: parties computed discordant sums {sums}"
            )

        return {
            "parties_count": self.parties_count,
            "aggregate_sum": sums[0],
            "average_salary": averages[0],
            "party_results": party_results,
        }
