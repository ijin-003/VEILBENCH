"""Durable, non-sensitive replay guards for a single MPC party.

Only session identifiers, lifecycle markers, and expiry timestamps are stored.
Founder salaries, capability tokens, MPyC shares, and computation results are
never written to this database.
"""

from __future__ import annotations

import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any


_ALLOWED_STATES = {"SUBMITTED", "COMPUTING", "COMPLETED", "FAILED", "SHUTDOWN", "EXPIRED"}
_TOMBSTONE_FALLBACK_SECONDS = 24 * 60 * 60


class PartyStateStore:
    """Small SQLite-backed guard store, isolated per party process/container."""

    def __init__(self, database_path: str) -> None:
        if not database_path or database_path == ":memory:":
            raise ValueError("MPC_PARTY_STATE_DB_PATH must be a persistent file path")
        self.database_path = str(Path(database_path).expanduser())
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        directory = Path(self.database_path).resolve().parent
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name != "nt":
            os.chmod(directory, 0o700)
        connection = sqlite3.connect(self.database_path, timeout=5.0, isolation_level=None)
        if os.name != "nt":
            os.chmod(self.database_path, 0o600)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS party_session_guards (
                    session_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    expires_at INTEGER NOT NULL,
                    input_submitted INTEGER NOT NULL DEFAULT 0,
                    updated_at INTEGER NOT NULL
                )
                """
            )

    def claim_submission(self, session_id: str, expires_at: int) -> str | None:
        """Atomically claim a capability once; return existing state on replay."""
        now = int(time.time())
        if int(expires_at) <= now:
            return "EXPIRED"
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "DELETE FROM party_session_guards WHERE expires_at <= ?", (now,)
            )
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO party_session_guards
                    (session_id, state, expires_at, input_submitted, updated_at)
                VALUES (?, 'SUBMITTED', ?, 1, ?)
                """,
                (session_id, int(expires_at), now),
            )
            if cursor.rowcount == 1:
                connection.commit()
                return None
            row = connection.execute(
                "SELECT state FROM party_session_guards WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            connection.commit()
            return str(row["state"]) if row is not None else "EXPIRED"

    def set_state(
        self,
        session_id: str,
        state: str,
        *,
        expires_at: int | None = None,
        input_submitted: bool | None = None,
    ) -> None:
        if state not in _ALLOWED_STATES:
            raise ValueError("Unsupported party session state")
        now = int(time.time())
        fallback_expiry = int(
            expires_at if expires_at is not None else now + _TOMBSTONE_FALLBACK_SECONDS
        )
        submitted_value = int(bool(input_submitted)) if input_submitted is not None else 0
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO party_session_guards
                    (session_id, state, expires_at, input_submitted, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    state = excluded.state,
                    expires_at = CASE
                        WHEN ? IS NULL THEN party_session_guards.expires_at
                        ELSE excluded.expires_at
                    END,
                    input_submitted = CASE
                        WHEN ? IS NULL THEN party_session_guards.input_submitted
                        ELSE MAX(party_session_guards.input_submitted, excluded.input_submitted)
                    END,
                    updated_at = excluded.updated_at
                """,
                (
                    session_id,
                    state,
                    fallback_expiry,
                    submitted_value,
                    now,
                    expires_at,
                    input_submitted,
                ),
            )
            connection.commit()

    def get(self, session_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT session_id, state, expires_at, input_submitted
                FROM party_session_guards WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def recover_incomplete(self) -> int:
        """Mark volatile sessions failed after a party process restart."""
        now = int(time.time())
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE party_session_guards
                SET state = 'FAILED', updated_at = ?
                WHERE state IN ('SUBMITTED', 'COMPUTING', 'COMPLETED')
                  AND expires_at > ?
                """,
                (now, now),
            )
            return cursor.rowcount

    def delete_expired(self, now: int | None = None) -> int:
        current_time = int(time.time()) if now is None else int(now)
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM party_session_guards WHERE expires_at <= ?",
                (current_time,),
            )
            return cursor.rowcount
