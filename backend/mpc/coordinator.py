"""Legacy test harness for running a three-input MPyC protocol locally.

This class accepts all three plaintext inputs in one process and is retained
only for local protocol/integration tests. The application API must use
``DistributedCoordinator``; it never accepts salary values.
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional

from backend.mpc.config import DEFAULT_BASE_PORT, DEFAULT_PARTIES_COUNT, MPC_TIMEOUT_SECONDS
from backend.mpc.exceptions import ConfigurationError, MPCTimeoutError, PartyDisconnectedError
from backend.mpc.validation import validate_salary

logger = logging.getLogger("veilbench.mpc.coordinator")


class MPCCoordinator:
    """Test-only runner that starts three separate MPyC processes locally."""

    def __init__(
        self,
        parties_count: int = DEFAULT_PARTIES_COUNT,
        base_port: int = DEFAULT_BASE_PORT,
        timeout: float = MPC_TIMEOUT_SECONDS,
    ):
        if parties_count != 3:
            raise ConfigurationError(
                f"VEILBENCH protocol strictly requires 3 parties, got {parties_count}"
            )
        self.parties_count = parties_count
        self.base_port = base_port
        self.timeout = timeout

    @staticmethod
    async def _stop_and_reap(
        processes: list[asyncio.subprocess.Process],
        communication: asyncio.Future | None = None,
    ) -> None:
        for process in processes:
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass

        if communication is not None:
            try:
                await asyncio.wait_for(asyncio.shield(communication), timeout=5)
            except asyncio.TimeoutError:
                communication.cancel()
                await asyncio.gather(communication, return_exceptions=True)
            except BaseException:
                # The process has already been killed; still wait for every
                # child below rather than leaking a pipe/transport exception.
                pass
            await asyncio.gather(*(process.wait() for process in processes), return_exceptions=True)
            return

        # If communication was never started (for example, process creation
        # failed partway through), close stdin and drain each process's pipes.
        await asyncio.gather(
            *(process.communicate() for process in processes if process.returncode is None),
            return_exceptions=True,
        )
        await asyncio.gather(*(process.wait() for process in processes), return_exceptions=True)

    async def execute_protocol(
        self,
        salaries: List[int],
        custom_base_port: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run the local test protocol; never use this method in the web API."""
        if len(salaries) != self.parties_count:
            raise ConfigurationError(
                f"Expected exactly {self.parties_count} inputs, got {len(salaries)}"
            )

        validated_salaries = [validate_salary(salary) for salary in salaries]
        base_port = custom_base_port or self.base_port
        base_cmd = [sys.executable, "-m", "backend.mpc.party_runner"]
        processes: list[asyncio.subprocess.Process] = []
        communication: asyncio.Future | None = None

        try:
            for party_id in range(self.parties_count):
                party_args = base_cmd + [
                    "-M", str(self.parties_count),
                    "-I", str(party_id),
                    "--base-port", str(base_port),
                ]
                process = await asyncio.create_subprocess_exec(
                    *party_args,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                processes.append(process)

            communications = [
                asyncio.create_task(
                    process.communicate(json.dumps(salary).encode("utf-8") + b"\n")
                )
                for process, salary in zip(processes, validated_salaries, strict=True)
            ]
            communication = asyncio.gather(*communications, return_exceptions=True)
            try:
                outputs = await asyncio.wait_for(
                    asyncio.shield(communication), timeout=self.timeout
                )
            except asyncio.TimeoutError as error:
                await self._stop_and_reap(processes, communication)
                raise MPCTimeoutError(
                    f"MPC computation timed out after {self.timeout} seconds"
                ) from error

            party_results: list[dict[str, Any]] = []
            for party_id, output in enumerate(outputs):
                if isinstance(output, BaseException):
                    raise PartyDisconnectedError(f"Party {party_id} process communication failed") from output
                stdout, _stderr = output
                if processes[party_id].returncode != 0:
                    raise PartyDisconnectedError(f"Party {party_id} exited unsuccessfully")
                output_text = stdout.decode("utf-8", errors="replace")
                if "__MPC_RESULT_START__" not in output_text:
                    raise PartyDisconnectedError(
                        f"Party {party_id} completed without valid MPC result markers"
                    )
                try:
                    result_text = output_text.split("__MPC_RESULT_START__", 1)[1].split(
                        "__MPC_RESULT_END__", 1
                    )[0]
                    party_results.append(json.loads(result_text))
                except (ValueError, TypeError, json.JSONDecodeError) as error:
                    raise PartyDisconnectedError(
                        f"Party {party_id} returned an invalid MPC result"
                    ) from error

            sums = [int(result["aggregate_sum"]) for result in party_results]
            averages = [float(result["average_salary"]) for result in party_results]
            if len(set(sums)) != 1 or len(set(averages)) != 1:
                raise ConfigurationError("MPC parties returned inconsistent aggregate results")

            return {
                "parties_count": self.parties_count,
                "aggregate_sum": sums[0],
                "average_salary": averages[0],
                "party_results": party_results,
            }
        except BaseException:
            if processes and any(process.returncode is None for process in processes):
                await self._stop_and_reap(processes, communication)
            raise
