"""Input validation that does not initialize the MPyC runtime."""

from typing import Any

from backend.mpc.config import MAX_SALARY, MIN_SALARY
from backend.mpc.exceptions import InvalidSalaryError


def validate_salary(salary: Any) -> int:
    """Reject non-integral and out-of-domain salary values before MPC input."""
    if isinstance(salary, bool) or not isinstance(salary, (int, float)):
        raise InvalidSalaryError(f"Salary must be a numeric integer, got {type(salary).__name__}")
    try:
        value = int(salary)
    except (ValueError, OverflowError) as error:
        raise InvalidSalaryError(f"Invalid salary numeric format: {error}") from error
    if salary != value:
        raise InvalidSalaryError("Salary must be a whole integer")
    if value < MIN_SALARY:
        raise InvalidSalaryError(f"Salary cannot be negative. Minimum allowed is ${MIN_SALARY:,}, got ${value:,}")
    if value > MAX_SALARY:
        raise InvalidSalaryError(f"Salary exceeds maximum limit of ${MAX_SALARY:,}, got ${value:,}")
    return value
