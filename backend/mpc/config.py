"""Cryptographic parameters and constraints for VEILBENCH MPC operations."""

# Salary bounds in USD
MIN_SALARY = 0
MAX_SALARY = 10_000_000

# Bit length for MPyC SecInt
# 32-bit field supports sums up to 2^32 - 1 = 4,294,967,295 (sufficient for 3 * $10M = $30M)
PRECISION_BITS = 32

# Multi-party default topology
DEFAULT_PARTIES_COUNT = 3
DEFAULT_THRESHOLD = 1
DEFAULT_BASE_PORT = 11365
MPC_TIMEOUT_SECONDS = 15.0
