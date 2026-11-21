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
)
from backend.tests.test_distributed import CONTROL_TOKEN, SESSION_ID, _make_party_app


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
async def test_rejected_input_is_not_echoed():
    module = _make_party_app()
    async with AsyncClient(transport=ASGITransport(app=module.app), base_url="http://test") as client:
        response = await client.post(f"/sessions/{SESSION_ID}/input",
                                     json={"salary": "PRIVATE-SALARY-SENTINEL"})
    assert response.status_code == 422
    assert "PRIVATE-SALARY-SENTINEL" not in response.text


@pytest.mark.asyncio
async def test_empty_party_reports_waiting_without_creating_input_state():
    module = _make_party_app()
    async with AsyncClient(transport=ASGITransport(app=module.app), base_url="http://test") as client:
        response = await client.get(f"/sessions/{SESSION_ID}/status",
                                    headers={"Authorization": f"Bearer {CONTROL_TOKEN}"})
    assert response.status_code == 200
    assert response.json()["input_submitted"] is False
    assert SESSION_ID not in module._sessions
