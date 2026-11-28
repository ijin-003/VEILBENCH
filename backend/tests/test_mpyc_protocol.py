"""Comprehensive Test Suite for VEILBENCH 3-Party Shamir-based MPC Protocol."""

import asyncio
import sys

import pytest

from backend.mpc.config import MAX_SALARY
from backend.mpc.coordinator import MPCCoordinator
from backend.mpc.exceptions import ConfigurationError, InvalidSalaryError
from backend.mpc.validation import validate_salary

pytestmark = pytest.mark.mpyc


@pytest.mark.asyncio
async def test_instructor_primary_scenario():
    """
    Instructor assigned primary test case:
    Party 0: 50,000
    Party 1: 70,000
    Party 2: 60,000
    Expected sum: 180,000
    Expected average: 60,000.0
    """
    coordinator = MPCCoordinator()
    salaries = [50000, 70000, 60000]

    result = await coordinator.execute_protocol(salaries, custom_base_port=12100)

    assert result["parties_count"] == 3
    assert result["aggregate_sum"] == 180000
    assert result["average_salary"] == 60000.0
    assert len(result["party_results"]) == 3

    # Verify each party independently verified the exact same consensus output
    for party_res in result["party_results"]:
        assert party_res["aggregate_sum"] == 180000
        assert party_res["average_salary"] == 60000.0


@pytest.mark.asyncio
async def test_different_salary_values():
    """Test MPC computation with arbitrary different salary figures."""
    coordinator = MPCCoordinator()
    salaries = [120000, 150000, 180000]

    result = await coordinator.execute_protocol(salaries, custom_base_port=12110)

    assert result["aggregate_sum"] == 450000
    assert result["average_salary"] == 150000.0


@pytest.mark.asyncio
async def test_zero_salary_input():
    """Test MPC computation when a founder inputs zero salary."""
    coordinator = MPCCoordinator()
    salaries = [0, 90000, 120000]

    result = await coordinator.execute_protocol(salaries, custom_base_port=12120)

    assert result["aggregate_sum"] == 210000
    assert result["average_salary"] == 70000.0


@pytest.mark.asyncio
async def test_maximum_allowed_input():
    """Test boundary condition with maximum allowable salary inputs ($10,000,000)."""
    coordinator = MPCCoordinator()
    salaries = [MAX_SALARY, MAX_SALARY, MAX_SALARY]

    result = await coordinator.execute_protocol(salaries, custom_base_port=12130)

    assert result["aggregate_sum"] == 30000000
    assert result["average_salary"] == float(MAX_SALARY)


def test_input_validation_negative_salary():
    """Negative inputs must be strictly rejected with InvalidSalaryError."""
    with pytest.raises(InvalidSalaryError, match="Salary cannot be negative"):
        validate_salary(-50000)


def test_input_validation_exceeds_maximum():
    """Inputs exceeding MAX_SALARY must be rejected with InvalidSalaryError."""
    with pytest.raises(InvalidSalaryError, match="Salary exceeds maximum limit"):
        validate_salary(MAX_SALARY + 1)


def test_input_validation_invalid_types():
    """Non-numeric or boolean values must be rejected."""
    with pytest.raises(InvalidSalaryError, match="Salary must be a numeric integer"):
        validate_salary("fifty thousand")

    with pytest.raises(InvalidSalaryError, match="Salary must be a numeric integer"):
        validate_salary(True)

    with pytest.raises(InvalidSalaryError, match="Salary must be a numeric integer"):
        validate_salary(None)


@pytest.mark.asyncio
async def test_coordinator_rejects_invalid_salaries():
    """Coordinator must reject any batch containing invalid inputs before launching processes."""
    coordinator = MPCCoordinator()
    with pytest.raises(InvalidSalaryError):
        await coordinator.execute_protocol([50000, -1000, 60000])

    with pytest.raises(InvalidSalaryError):
        await coordinator.execute_protocol([50000, MAX_SALARY + 100, 60000])


@pytest.mark.asyncio
async def test_invalid_party_configuration():
    """Coordinator must reject requests with wrong number of participants."""
    coordinator = MPCCoordinator()

    with pytest.raises(ConfigurationError, match="Expected exactly 3 inputs"):
        await coordinator.execute_protocol([50000, 60000])

    with pytest.raises(ConfigurationError, match="Expected exactly 3 inputs"):
        await coordinator.execute_protocol([50000, 60000, 70000, 80000])


@pytest.mark.asyncio
async def test_repeated_executions():
    """
    Verify repeated executions succeed consistently without port collisions
    or lingering process state.
    """
    coordinator = MPCCoordinator()

    run1 = await coordinator.execute_protocol([40000, 50000, 60000], custom_base_port=12140)
    assert run1["aggregate_sum"] == 150000
    assert run1["average_salary"] == 50000.0

    run2 = await coordinator.execute_protocol([80000, 90000, 100000], custom_base_port=12150)
    assert run2["aggregate_sum"] == 270000
    assert run2["average_salary"] == 90000.0

    run3 = await coordinator.execute_protocol([100000, 200000, 300000], custom_base_port=12160)
    assert run3["aggregate_sum"] == 600000
    assert run3["average_salary"] == 200000.0


@pytest.mark.asyncio
async def test_disconnected_party_handling():
    """
    Test fault injection: simulate a disconnected/failed party.
    When a required computing party is missing, the MPC protocol cannot finish.
    """
    base_cmd = [
        sys.executable,
        "-m",
        "backend.mpc.party_runner",
    ]
    procs = []
    base_port = 12170

    # Start only 2 of the 3 required parties
    for i in range(2):
        party_args = base_cmd + [
            "-M",
            "3",
            "-I",
            str(i),
            "--base-port",
            str(base_port),
        ]
        p = await asyncio.create_subprocess_exec(
            *party_args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
stderr=asyncio.subprocess.DEVNULL,
        )
        procs.append(p)
        p.stdin.write(b"50000\n")
        await p.stdin.drain()
        p.stdin.close()

    try:
        # Give 1.5 seconds to attempt connection
        tasks = [asyncio.create_task(p.wait()) for p in procs]
        done, pending = await asyncio.wait(tasks, timeout=1.5)

        # Computation must NOT complete successfully without party 2
        assert len(done) == 0
    finally:
        for p in procs:
            try:
                p.kill()
                await p.wait()
            except (ProcessLookupError, OSError):
                pass
        await asyncio.gather(*tasks, return_exceptions=True)


@pytest.mark.asyncio
async def test_zero_knowledge_isolation():
    """
    Confidentiality verification:
    Verify that each party process's output contains ONLY the aggregate sum
    and average, and contains NO plaintext inputs of other parties.
    """
    coordinator = MPCCoordinator()
    # Choose values where average (62,000) does not coincide with any input
    salaries = [51000, 72000, 63000]

    result = await coordinator.execute_protocol(salaries, custom_base_port=12180)

    for i, party_res in enumerate(result["party_results"]):
        # Verify the returned structure contains only the agreed-upon public aggregate
        assert set(party_res.keys()) == {
            "party_id",
            "parties_count",
            "threshold",
            "aggregate_sum",
            "average_salary",
        }
        # Other parties' private salaries must not be exposed in party_res
        for j, other_salary in enumerate(salaries):
            if j != i:
                assert party_res["aggregate_sum"] != other_salary
                assert party_res["average_salary"] != float(other_salary)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("salaries", "expected_sum", "expected_avg", "base_port"),
    [
        ([0, 0, 0], 0, 0.0, 12190),
        ([100, 200, 300], 600, 200.0, 12200),
        ([1, 2, 4], 7, 7.0 / 3.0, 12210),
        ([1000000, 2000000, 3000000], 6000000, 2000000.0, 12220),
    ],
)
async def test_audit_required_synthetic_computations(
    salaries: list[int], expected_sum: int, expected_avg: float, base_port: int
):
    """Verify genuine 3-party MPyC computation across all required audit test vectors."""
    coordinator = MPCCoordinator()
    result = await coordinator.execute_protocol(salaries, custom_base_port=base_port)
    assert result["parties_count"] == 3
    assert result["aggregate_sum"] == expected_sum
    assert result["average_salary"] == pytest.approx(expected_avg)
    for party_res in result["party_results"]:
        assert party_res["aggregate_sum"] == expected_sum
        assert party_res["average_salary"] == pytest.approx(expected_avg)
