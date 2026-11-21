"""Exception classes for VEILBENCH MPC operations."""


class MPCError(Exception):
    """Base exception for all MPC-related errors."""
    pass


class InvalidSalaryError(MPCError):
    """Raised when participant salary input fails cryptographic bounds validation."""
    pass


class PartyDisconnectedError(MPCError):
    """Raised when an MPC compute party fails, drops out, or terminates prematurely."""
    pass


class MPCTimeoutError(MPCError):
    """Raised when an MPC execution exceeds the synchronization timeout threshold."""
    pass


class ConfigurationError(MPCError):
    """Raised when party configuration violates honest majority or cryptographic constraints."""
    pass
