"""Regression tests for privacy errors, waiting status and key separation."""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from backend.models import BenchmarkSession
from backend.security.tokens import FounderTokenError, issue_founder_token, verify_founder_token
from backend.services.session_service import (
    SessionLifecycleError,
    compute_session,
    refresh_submission_state,
    recover_session,
)
from backend.tests.test_distributed import CONTROL_TOKEN, SESSION_ID, _make_party_app
from backend.mpc.exceptions import MPCExecutionFailed, MPCRecoveryRequired


def ready_session():
    return BenchmarkSession(id=SESSION_ID, state="ready", submitted_party_ids=[0, 1, 2],
                            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5))


@pytest.mark.asyncio
async def test_active_computation_blocks_admission():
    db, coordinator = AsyncMock(), AsyncMock()
    db.scalar.return_value = "another-session"
    with pytest.raises(SessionLifecycleError, match="active"):
        await compute_session(db, ready_session(), coordinator)
    coordinator.execute_protocol.assert_not_awaited()
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_computation_keeps_persistent_barrier():
    db, coordinator = AsyncMock(), AsyncMock()
    db.scalar.return_value = None
    coordinator.execute_protocol.side_effect = TimeoutError()
    record = ready_session()
    with pytest.raises(TimeoutError):
        await compute_session(db, record, coordinator)
    assert record.state == "computing"
    assert "recovery" in record.failure_reason
    assert db.commit.await_count == 2


@pytest.mark.asyncio
async def test_completed_result_is_not_recomputed():
    db, coordinator = AsyncMock(), AsyncMock()
    record = ready_session()
    record.state = "completed"
    assert await compute_session(db, record, coordinator) is record
    coordinator.execute_protocol.assert_not_awaited()


@pytest.mark.asyncio
async def test_expiry_is_committed_before_error():
    db, coordinator = AsyncMock(), AsyncMock()
    record = ready_session()
    record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    with pytest.raises(SessionLifecycleError, match="expired"):
        await refresh_submission_state(db, record, coordinator)
    assert record.state == "expired"
    db.commit.assert_awaited_once()
    coordinator.get_statuses.assert_not_awaited()


def test_party_secret_cannot_forge_another_party_capability():
    forged = issue_founder_token("party-zero-key", SESSION_ID, 1, int(time.time()) + 60)
    with pytest.raises(FounderTokenError):
        verify_founder_token(forged, "party-one-key", SESSION_ID, 1)


@pytest.mark.asyncio
async def test_rejected_input_is_not_echoed(tmp_path):
    module = _make_party_app(state_db_path=tmp_path / "party-state.sqlite3")
    async with AsyncClient(transport=ASGITransport(app=module.app), base_url="http://test") as client:
        response = await client.post(f"/sessions/{SESSION_ID}/input",
                                     json={"salary": "PRIVATE-SALARY-SENTINEL"})
    assert response.status_code == 422
    assert "PRIVATE-SALARY-SENTINEL" not in response.text


@pytest.mark.asyncio
async def test_empty_party_reports_waiting_without_creating_input_state(tmp_path):
    module = _make_party_app(state_db_path=tmp_path / "party-state.sqlite3")
    async with AsyncClient(transport=ASGITransport(app=module.app), base_url="http://test") as client:
        response = await client.get(f"/sessions/{SESSION_ID}/status",
                                    headers={"Authorization": f"Bearer {CONTROL_TOKEN}"})
    assert response.status_code == 200
    assert response.json()["input_submitted"] is False
    assert SESSION_ID not in module._sessions


@pytest.mark.asyncio
async def test_confirmed_cleanup_marks_failed_attempt_terminal():
    db, coordinator = AsyncMock(), AsyncMock()
    db.scalar.return_value = None
    coordinator.execute_protocol.side_effect = MPCExecutionFailed("safe failure")
    record = ready_session()

    with pytest.raises(MPCExecutionFailed):
        await compute_session(db, record, coordinator)

    assert record.state == "failed"
    assert "cleared" in record.failure_reason


@pytest.mark.asyncio
async def test_operator_recovery_releases_barrier_after_all_parties_confirm():
    db, coordinator = AsyncMock(), AsyncMock()
    record = ready_session()
    record.state = "computing"

    recovered = await recover_session(db, record, coordinator)

    coordinator.shutdown_session.assert_awaited_once_with(
        SESSION_ID, expires_at=int(record.expires_at.timestamp())
    )
    assert recovered.state == "failed"
    assert "recovered" in recovered.failure_reason


@pytest.mark.asyncio
async def test_operator_recovery_keeps_barrier_if_cleanup_is_unconfirmed():
    db, coordinator = AsyncMock(), AsyncMock()
    coordinator.shutdown_session.side_effect = MPCRecoveryRequired("party offline")
    record = ready_session()
    record.state = "computing"

    with pytest.raises(MPCRecoveryRequired):
        await recover_session(db, record, coordinator)

    assert record.state == "computing"
    assert "still required" in record.failure_reason


@pytest.mark.asyncio
async def test_restarted_party_state_fails_session_closed():
    db, coordinator = AsyncMock(), AsyncMock()
    coordinator.get_statuses.return_value = [
        {"party_id": 0, "state": "FAILED", "input_submitted": True},
        {"party_id": 1, "state": "WAITING_FOR_PARTICIPANTS", "input_submitted": True},
        {"party_id": 2, "state": "WAITING_FOR_PARTICIPANTS", "input_submitted": True},
    ]
    record = ready_session()
    record.state = "created"

    refreshed = await refresh_submission_state(db, record, coordinator)

    assert refreshed.state == "failed"
    assert "Create a new" in refreshed.failure_reason
