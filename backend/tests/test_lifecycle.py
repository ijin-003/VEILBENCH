"""Tests for PartyLifecycle state machine (backend.mpc.lifecycle)."""

import pytest

from backend.mpc.lifecycle import VALID_TRANSITIONS, PartyLifecycle, PartyState

# ── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture
def lifecycle():
    """Create a fresh lifecycle for party 0 in session 'test-session'."""
    return PartyLifecycle(party_id=0, session_id="test-session")


# ── Initial state ────────────────────────────────────────────────────────────

def test_initial_state(lifecycle):
    assert lifecycle.state == PartyState.INITIALIZING
    assert lifecycle.input_submitted is False


def test_initial_to_dict(lifecycle):
    d = lifecycle.to_dict()
    assert d["party_id"] == 0
    assert d["session_id"] == "test-session"
    assert d["state"] == "INITIALIZING"
    assert d["input_submitted"] is False
    assert "uptime_seconds" in d


def test_initial_history(lifecycle):
    history = lifecycle.get_history()
    assert len(history) == 1
    assert history[0]["state"] == "INITIALIZING"
    assert "timestamp" in history[0]


# ── Happy path transitions ──────────────────────────────────────────────────

def test_full_happy_path(lifecycle):
    """Walk through the complete happy-path lifecycle."""
    lifecycle.transition(PartyState.WAITING_FOR_PARTICIPANTS)
    assert lifecycle.state == PartyState.WAITING_FOR_PARTICIPANTS

    lifecycle.transition(PartyState.READY)
    assert lifecycle.state == PartyState.READY

    lifecycle.transition(PartyState.COMPUTING)
    assert lifecycle.state == PartyState.COMPUTING

    lifecycle.transition(PartyState.COMPLETED)
    assert lifecycle.state == PartyState.COMPLETED

    lifecycle.transition(PartyState.SHUTDOWN)
    assert lifecycle.state == PartyState.SHUTDOWN

    # History should have 6 entries (init + 5 transitions)
    assert len(lifecycle.get_history()) == 6


def test_failed_then_shutdown(lifecycle):
    """Failure at any state should allow transition to SHUTDOWN."""
    lifecycle.transition(PartyState.WAITING_FOR_PARTICIPANTS)
    lifecycle.transition(PartyState.READY)
    lifecycle.transition(PartyState.FAILED)
    assert lifecycle.state == PartyState.FAILED

    lifecycle.transition(PartyState.SHUTDOWN)
    assert lifecycle.state == PartyState.SHUTDOWN


def test_initializing_to_failed(lifecycle):
    """Failure during initialization."""
    lifecycle.transition(PartyState.FAILED)
    assert lifecycle.state == PartyState.FAILED


def test_initializing_to_shutdown(lifecycle):
    """Shutdown during initialization."""
    lifecycle.transition(PartyState.SHUTDOWN)
    assert lifecycle.state == PartyState.SHUTDOWN


# ── Invalid transitions ─────────────────────────────────────────────────────

def test_cannot_skip_states(lifecycle):
    """Cannot jump from INITIALIZING directly to COMPUTING."""
    with pytest.raises(ValueError, match="illegal transition"):
        lifecycle.transition(PartyState.COMPUTING)


def test_cannot_go_back(lifecycle):
    """Cannot go from READY back to INITIALIZING."""
    lifecycle.transition(PartyState.WAITING_FOR_PARTICIPANTS)
    lifecycle.transition(PartyState.READY)
    with pytest.raises(ValueError, match="illegal transition"):
        lifecycle.transition(PartyState.INITIALIZING)


def test_cannot_transition_from_shutdown(lifecycle):
    """SHUTDOWN is a terminal state — no outgoing transitions."""
    lifecycle.transition(PartyState.FAILED)
    lifecycle.transition(PartyState.SHUTDOWN)
    with pytest.raises(ValueError, match="illegal transition"):
        lifecycle.transition(PartyState.INITIALIZING)


def test_cannot_go_from_completed_to_computing(lifecycle):
    """Cannot re-enter COMPUTING from COMPLETED."""
    lifecycle.transition(PartyState.WAITING_FOR_PARTICIPANTS)
    lifecycle.transition(PartyState.READY)
    lifecycle.transition(PartyState.COMPUTING)
    lifecycle.transition(PartyState.COMPLETED)
    with pytest.raises(ValueError, match="illegal transition"):
        lifecycle.transition(PartyState.COMPUTING)


# ── All transitions in VALID_TRANSITIONS are reachable ───────────────────────

def test_valid_transitions_completeness():
    """Every PartyState must appear as a key in VALID_TRANSITIONS."""
    for state in PartyState:
        assert state in VALID_TRANSITIONS, f"{state} missing from VALID_TRANSITIONS"


# ── Double-submission prevention ─────────────────────────────────────────────

def test_mark_input_submitted(lifecycle):
    """First submission should succeed."""
    lifecycle.mark_input_submitted()
    assert lifecycle.input_submitted is True


def test_double_submission_rejected(lifecycle):
    """Second submission attempt must raise ValueError."""
    lifecycle.mark_input_submitted()
    with pytest.raises(ValueError, match="already submitted"):
        lifecycle.mark_input_submitted()


def test_double_submission_flag_in_to_dict(lifecycle):
    """to_dict() reflects input_submitted state accurately."""
    assert lifecycle.to_dict()["input_submitted"] is False
    lifecycle.mark_input_submitted()
    assert lifecycle.to_dict()["input_submitted"] is True


# ── Serialization ────────────────────────────────────────────────────────────

def test_to_dict_after_transitions(lifecycle):
    """to_dict() should reflect the current state after transitions."""
    lifecycle.transition(PartyState.WAITING_FOR_PARTICIPANTS)
    lifecycle.transition(PartyState.READY)
    d = lifecycle.to_dict()
    assert d["state"] == "READY"


def test_history_records_all_transitions(lifecycle):
    """get_history() length matches transition count + 1 (initial)."""
    lifecycle.transition(PartyState.WAITING_FOR_PARTICIPANTS)
    lifecycle.transition(PartyState.READY)
    lifecycle.transition(PartyState.COMPUTING)
    history = lifecycle.get_history()
    assert len(history) == 4
    states = [h["state"] for h in history]
    assert states == ["INITIALIZING", "WAITING_FOR_PARTICIPANTS", "READY", "COMPUTING"]


# ── No private data in serialization ─────────────────────────────────────────

def test_no_private_data_in_to_dict(lifecycle):
    """to_dict() must NEVER contain salary, shares, or input values."""
    lifecycle.mark_input_submitted()
    d = lifecycle.to_dict()
    # Only allowed keys
    allowed_keys = {"party_id", "session_id", "state", "input_submitted", "uptime_seconds"}
    assert set(d.keys()) == allowed_keys


def test_no_private_data_in_history(lifecycle):
    """get_history() entries must only have state and timestamp."""
    lifecycle.transition(PartyState.WAITING_FOR_PARTICIPANTS)
    for entry in lifecycle.get_history():
        assert set(entry.keys()) == {"state", "timestamp"}


# ── Multiple party instances ─────────────────────────────────────────────────

def test_independent_party_lifecycles():
    """Two lifecycle instances should be fully independent."""
    lc0 = PartyLifecycle(party_id=0, session_id="s1")
    lc1 = PartyLifecycle(party_id=1, session_id="s1")

    lc0.transition(PartyState.WAITING_FOR_PARTICIPANTS)
    lc0.mark_input_submitted()

    # lc1 is unaffected
    assert lc1.state == PartyState.INITIALIZING
    assert lc1.input_submitted is False
