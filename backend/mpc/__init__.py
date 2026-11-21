"""VEILBENCH MPC package.

Keep MPyC imports lazy: importing the coordinator web API must not initialize
an MPyC runtime. This keeps health checks and metadata tests independent from
the platform-specific MPyC event-loop setup.
"""

from backend.mpc.config import MAX_SALARY, MIN_SALARY, PRECISION_BITS
from backend.mpc.exceptions import (
    ConfigurationError,
    InvalidSalaryError,
    MPCError,
    MPCTimeoutError,
    PartyDisconnectedError,
)
from backend.mpc.lifecycle import PartyLifecycle, PartyState
from backend.mpc.validation import validate_salary

__all__ = [
    "MPCCoordinator", "DistributedCoordinator", "PartyLifecycle", "PartyState", "run_mpc_summation",
    "validate_salary", "MIN_SALARY", "MAX_SALARY", "PRECISION_BITS", "MPCError", "InvalidSalaryError",
    "PartyDisconnectedError", "MPCTimeoutError", "ConfigurationError",
]


def __getattr__(name: str):
    if name == "MPCCoordinator":
        from backend.mpc.coordinator import MPCCoordinator
        return MPCCoordinator
    if name == "DistributedCoordinator":
        from backend.mpc.distributed_coordinator import DistributedCoordinator
        return DistributedCoordinator
    if name == "run_mpc_summation":
        from backend.mpc.protocol import run_mpc_summation
        return run_mpc_summation
    raise AttributeError(name)
