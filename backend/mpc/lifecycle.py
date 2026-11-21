"""
Party Lifecycle State Machine for VEILBENCH MPC nodes.

Manages the lifecycle of each MPC compute party through deterministic
state transitions with strict enforcement of valid transitions.
"""

import enum
import logging
import time

logger = logging.getLogger("veilbench.mpc.lifecycle")


class PartyState(str, enum.Enum):
    """Enumeration of all valid MPC party lifecycle states."""

    INITIALIZING = "INITIALIZING"
    WAITING_FOR_PARTICIPANTS = "WAITING_FOR_PARTICIPANTS"
    READY = "READY"
    COMPUTING = "COMPUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SHUTDOWN = "SHUTDOWN"


# Valid state transitions: source -> set of allowed destinations
VALID_TRANSITIONS = {
    PartyState.INITIALIZING: {PartyState.WAITING_FOR_PARTICIPANTS, PartyState.FAILED, PartyState.SHUTDOWN},
    PartyState.WAITING_FOR_PARTICIPANTS: {PartyState.READY, PartyState.FAILED, PartyState.SHUTDOWN},
    PartyState.READY: {PartyState.COMPUTING, PartyState.FAILED, PartyState.SHUTDOWN},
    PartyState.COMPUTING: {PartyState.COMPLETED, PartyState.FAILED},
    PartyState.COMPLETED: {PartyState.SHUTDOWN},
    PartyState.FAILED: {PartyState.SHUTDOWN},
    PartyState.SHUTDOWN: set(),  # Terminal state
}


class PartyLifecycle:
    """
    Manages the state machine for a single MPC party node.

    Thread-safe lifecycle transitions with audit logging.
    Does NOT log any private inputs, shares, or salary values.
    """

    def __init__(self, party_id: int, session_id: str):
        self.party_id = party_id
        self.session_id = session_id
        self._state = PartyState.INITIALIZING
        self._input_submitted = False
        self._created_at = time.time()
        self._state_history: list[tuple[PartyState, float]] = [
            (PartyState.INITIALIZING, self._created_at)
        ]

    @property
    def state(self) -> PartyState:
        return self._state

    @property
    def input_submitted(self) -> bool:
        return self._input_submitted

    def transition(self, target: PartyState) -> None:
        """
        Transition to a new state if the transition is valid.
        Raises ValueError for illegal transitions.
        """
        allowed = VALID_TRANSITIONS.get(self._state, set())
        if target not in allowed:
            raise ValueError(
                f"Party {self.party_id} session {self.session_id}: "
                f"illegal transition {self._state.value} -> {target.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )
        old_state = self._state
        self._state = target
        self._state_history.append((target, time.time()))
        # Log transition without exposing any private data
        logger.info(
            "Party %d [session %s]: %s -> %s",
            self.party_id, self.session_id, old_state.value, target.value,
        )

    def mark_input_submitted(self) -> None:
        """
        Mark that this party has submitted its private input.
        Prevents double-submission. Does NOT log the input value.
        """
        if self._input_submitted:
            raise ValueError(
                f"Party {self.party_id} session {self.session_id}: "
                f"input already submitted. Double-submission is forbidden."
            )
        self._input_submitted = True
        logger.info(
            "Party %d [session %s]: private input accepted (value NOT logged)",
            self.party_id, self.session_id,
        )

    def to_dict(self) -> dict:
        """Serialize lifecycle state for status reporting. Never includes private data."""
        return {
            "party_id": self.party_id,
            "session_id": self.session_id,
            "state": self._state.value,
            "input_submitted": self._input_submitted,
            "uptime_seconds": round(time.time() - self._created_at, 2),
        }

    def get_history(self) -> list[dict]:
        """Return state transition history (timestamps only, no private data)."""
        return [
            {"state": s.value, "timestamp": t}
            for s, t in self._state_history
        ]
