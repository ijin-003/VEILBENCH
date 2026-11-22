import time

from backend.mpc.party_state_store import PartyStateStore


def test_capability_claim_is_atomic_and_single_use(tmp_path):
    store = PartyStateStore(str(tmp_path / "party.sqlite3"))
    expiry = int(time.time()) + 120

    assert store.claim_submission("session-a", expiry) is None
    assert store.claim_submission("session-a", expiry) == "SUBMITTED"
    assert store.get("session-a")["input_submitted"] == 1


def test_shutdown_tombstone_prevents_first_submission(tmp_path):
    store = PartyStateStore(str(tmp_path / "party.sqlite3"))
    expiry = int(time.time()) + 120

    store.set_state("session-a", "SHUTDOWN", expires_at=expiry)

    assert store.claim_submission("session-a", expiry) == "SHUTDOWN"
    assert store.get("session-a")["input_submitted"] == 0


def test_state_survives_store_recreation(tmp_path):
    path = str(tmp_path / "party.sqlite3")
    first_store = PartyStateStore(path)
    expiry = int(time.time()) + 120
    assert first_store.claim_submission("session-a", expiry) is None

    restarted_store = PartyStateStore(path)
    assert restarted_store.recover_incomplete() == 1
    assert restarted_store.get("session-a")["state"] == "FAILED"
    assert restarted_store.claim_submission("session-a", expiry) == "FAILED"


def test_expired_guards_are_pruned(tmp_path):
    store = PartyStateStore(str(tmp_path / "party.sqlite3"))
    store.set_state("old-session", "SHUTDOWN", expires_at=10)

    assert store.delete_expired(now=11) == 1
    assert store.get("old-session") is None


def test_expired_capability_cannot_be_claimed(tmp_path):
    store = PartyStateStore(str(tmp_path / "party.sqlite3"))
    assert store.claim_submission("expired-session", int(time.time()) - 1) == "EXPIRED"
    assert store.get("expired-session") is None


def test_persistent_guard_schema_contains_no_private_values(tmp_path):
    import sqlite3

    path = tmp_path / "party.sqlite3"
    PartyStateStore(str(path))
    with sqlite3.connect(path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(party_session_guards)")
        }

    assert columns == {"session_id", "state", "expires_at", "input_submitted", "updated_at"}
    assert not any("salary" in column or "token" in column or "share" in column for column in columns)
