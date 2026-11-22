"""Unit tests for direct founder submission and safe coordinator orchestration."""

import importlib
import os
import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from backend.security.tokens import issue_founder_token

CONTROL_TOKEN = "test-control-token"
FOUNDER_SECRET = "test-founder-signing-secret"
SESSION_ID = "test-session-123"


def _make_party_app(party_id: int = 0, state_db_path=None):
    if state_db_path is None:
        import tempfile
        from pathlib import Path

        state_db_path = Path(tempfile.mkdtemp()) / f"party_{party_id}.sqlite3"
    os.environ.update(
        {
            "MPC_PARTY_ID": str(party_id),
            "MPC_PARTIES_COUNT": "3",
            "MPC_COORDINATOR_TOKEN": CONTROL_TOKEN,
            "MPC_FOUNDER_TOKEN_SECRET": FOUNDER_SECRET,
            "MPC_ENABLE_TLS": "false",
            "MPC_BASE_PORT": "11365",
            "MPC_PARTY_STATE_DB_PATH": str(state_db_path),
        }
    )
    import backend.mpc.party_service as party_service

    return importlib.reload(party_service)


@pytest.fixture
def party_module(tmp_path):
    return _make_party_app(state_db_path=tmp_path / "party-state.sqlite3")


@pytest.fixture
async def party_client(party_module):
    async with AsyncClient(transport=ASGITransport(app=party_module.app), base_url="http://test-party") as client:
        yield client


def _control_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {CONTROL_TOKEN}"}


def _founder_headers(session_id: str = SESSION_ID, party_id: int = 0) -> dict[str, str]:
    token = issue_founder_token(FOUNDER_SECRET, session_id, party_id, int(time.time()) + 60)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_health_discloses_no_session_or_input(party_client):
    response = await party_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "party_id": 0, "mpyc_tls_enabled": False}


@pytest.mark.asyncio
async def test_founder_must_use_party_scoped_capability(party_client):
    response = await party_client.post(f"/sessions/{SESSION_ID}/input", json={"salary": 50000})
    assert response.status_code == 401

    response = await party_client.post(
        f"/sessions/{SESSION_ID}/input", json={"salary": 50000}, headers=_founder_headers(party_id=1)
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_direct_input_is_single_use_and_hidden_from_status(party_client):
    response = await party_client.post(
        f"/sessions/{SESSION_ID}/input", json={"salary": 50000}, headers=_founder_headers()
    )
    assert response.status_code == 200
    assert response.json()["input_submitted"] is True

    duplicate = await party_client.post(
        f"/sessions/{SESSION_ID}/input", json={"salary": 60000}, headers=_founder_headers()
    )
    assert duplicate.status_code == 409

    state = await party_client.get(f"/sessions/{SESSION_ID}/status", headers=_control_headers())
    assert state.status_code == 200
    assert state.json()["input_submitted"] is True
    assert "50000" not in state.text


@pytest.mark.asyncio
async def test_legacy_global_input_route_is_not_exposed(party_client):
    response = await party_client.post("/input", json={"salary": 50000}, headers=_control_headers())
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_control_token_cannot_be_used_as_a_founder_token(party_client):
    response = await party_client.post(
        f"/sessions/{SESSION_ID}/input", json={"salary": 50000}, headers=_control_headers()
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_compute_uses_mpc_runner_then_purges_private_input(party_client, party_module):
    await party_client.post(
        f"/sessions/{SESSION_ID}/input", json={"salary": 75000}, headers=_founder_headers()
    )
    mock_result = {
        "party_id": 0,
        "aggregate_sum": 180000,
        "average_salary": 60000.0,
        "parties_count": 3,
        "threshold": 1,
    }
    with patch.object(party_module, "_run_mpyc_computation", new=AsyncMock(return_value=mock_result)):
        response = await party_client.post(f"/sessions/{SESSION_ID}/compute", headers=_control_headers())
    assert response.status_code == 200
    assert response.json()["aggregate_sum"] == 180000
    assert party_module._sessions[SESSION_ID].private_input is None

    cleared = await party_client.post(f"/sessions/{SESSION_ID}/shutdown", headers=_control_headers())
    assert cleared.status_code == 200
    result = await party_client.get(f"/sessions/{SESSION_ID}/result", headers=_control_headers())
    assert result.status_code == 404


class TestDistributedCoordinator:
    def test_rejects_plain_http_when_tls_is_required(self):
        from backend.mpc.distributed_coordinator import DistributedCoordinator
        from backend.mpc.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError, match="HTTPS"):
            DistributedCoordinator(
                ["http://a", "http://b", "http://c"], ["a", "b", "c"], require_tls=True
            )

    @pytest.mark.asyncio
    async def test_it_orchestrates_only_metadata_and_aggregate(self):
        from backend.mpc.distributed_coordinator import DistributedCoordinator

        seen_paths: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen_paths.append(request.url.path)
            if request.url.path.endswith("/status"):
                party_id = int(request.url.host[-1])
                return httpx.Response(200, json={"party_id": party_id, "input_submitted": True})
            if request.url.path.endswith("/compute"):
                return httpx.Response(
                    200,
                    json={"aggregate_sum": 180000, "average_salary": 60000.0,
                          "session_id": SESSION_ID, "party_id": int(request.url.host[-1]),
                          "parties_count": 3, "threshold": 1},
                )
            return httpx.Response(200, json={"status": "cleared"})

        coordinator = DistributedCoordinator(
            ["http://party0", "http://party1", "http://party2"],
            ["a", "b", "c"],
            require_tls=False,
        )
        coordinator._client = lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))  # type: ignore[method-assign]
        statuses = await coordinator.get_statuses(SESSION_ID)
        result = await coordinator.execute_protocol(SESSION_ID)

        assert [item["party_id"] for item in statuses] == [0, 1, 2]
        assert result == {"parties_count": 3, "aggregate_sum": 180000, "average_salary": 60000.0}
        assert all("salary" not in path for path in seen_paths)

import time

@pytest.mark.asyncio
async def test_expired_founder_capability_rejected_by_api(party_client, party_module):
    expired_token = issue_founder_token(
        FOUNDER_SECRET, SESSION_ID, 0, int(time.time()) - 10
    )

    response = await party_client.post(
        f"/sessions/{SESSION_ID}/input",
        json={"salary": 50000},
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 403
    assert SESSION_ID not in party_module._sessions


@pytest.mark.asyncio
async def test_control_endpoints_reject_missing_authentication(party_client):
    endpoints = [
        ("get", f"/sessions/{SESSION_ID}/status"),
        ("post", f"/sessions/{SESSION_ID}/compute"),
        ("get", f"/sessions/{SESSION_ID}/result"),
        ("post", f"/sessions/{SESSION_ID}/shutdown"),
    ]

    for method, path in endpoints:
        response = await getattr(party_client, method)(path)
        assert response.status_code == 401, f"{method.upper()} {path} accepted unauthenticated request"


@pytest.mark.asyncio
async def test_founder_capability_cannot_be_reused_after_shutdown(party_client):
    headers = _founder_headers()

    first = await party_client.post(
        f"/sessions/{SESSION_ID}/input",
        json={"salary": 50000},
        headers=headers,
    )
    assert first.status_code == 200

    shutdown = await party_client.post(
        f"/sessions/{SESSION_ID}/shutdown",
        headers=_control_headers(),
    )
    assert shutdown.status_code == 200

    replay = await party_client.post(
        f"/sessions/{SESSION_ID}/input",
        json={"salary": 50000},
        headers=headers,
    )
    assert replay.status_code == 410

@pytest.mark.asyncio
async def test_founder_capability_replay_is_rejected_after_party_restart(tmp_path):
    state_db_path = tmp_path / "persistent-party-state.sqlite3"
    first_module = _make_party_app(state_db_path=state_db_path)
    headers = _founder_headers()
    async with AsyncClient(
        transport=ASGITransport(app=first_module.app), base_url="http://first-party"
    ) as client:
        response = await client.post(
            f"/sessions/{SESSION_ID}/input", json={"salary": 50000}, headers=headers
        )
    assert response.status_code == 200

    # Reloading the module models a process restart: volatile input memory is lost,
    # but the persistent consumed-capability marker remains.
    restarted_module = _make_party_app(state_db_path=state_db_path)
    restarted_module._state_store.recover_incomplete()
    async with AsyncClient(
        transport=ASGITransport(app=restarted_module.app), base_url="http://restarted-party"
    ) as client:
        replay = await client.post(
            f"/sessions/{SESSION_ID}/input", json={"salary": 50000}, headers=headers
        )
        status_response = await client.get(
            f"/sessions/{SESSION_ID}/status", headers=_control_headers()
        )
    assert replay.status_code == 410
    assert status_response.json()["state"] == "FAILED"
    assert status_response.json()["input_submitted"] is True


@pytest.mark.asyncio
async def test_shutdown_before_input_creates_replay_tombstone(party_client):
    shutdown = await party_client.post(
        f"/sessions/{SESSION_ID}/shutdown", headers=_control_headers()
    )
    assert shutdown.status_code == 200

    replay = await party_client.post(
        f"/sessions/{SESSION_ID}/input",
        json={"salary": 50000},
        headers=_founder_headers(),
    )
    assert replay.status_code == 410


@pytest.mark.asyncio
async def test_shutdown_retries_until_all_parties_confirm_cleanup():
    from backend.mpc.distributed_coordinator import DistributedCoordinator

    attempts = {0: 0, 1: 0, 2: 0}

    def handler(request: httpx.Request) -> httpx.Response:
        party_id = int(request.url.host[-1])
        if request.url.path.endswith("/shutdown"):
            attempts[party_id] += 1
            if attempts[party_id] < 3:
                return httpx.Response(503)
            return httpx.Response(200, json={"status": "cleared"})
        return httpx.Response(200, json={})

    coordinator = DistributedCoordinator(
        ["http://party0", "http://party1", "http://party2"],
        ["a", "b", "c"],
        require_tls=False,
    )
    coordinator._client = lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))  # type: ignore[method-assign]

    await coordinator.shutdown_session(SESSION_ID, expires_at=int(time.time()) + 60)

    assert attempts == {0: 3, 1: 3, 2: 3}


@pytest.mark.asyncio
async def test_cleanup_failure_requires_operator_recovery():
    from backend.mpc.distributed_coordinator import DistributedCoordinator
    from backend.mpc.exceptions import MPCRecoveryRequired

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/shutdown"):
            return httpx.Response(503)
        return httpx.Response(200, json={})

    coordinator = DistributedCoordinator(
        ["http://party0", "http://party1", "http://party2"],
        ["a", "b", "c"],
        require_tls=False,
    )
    coordinator._client = lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))  # type: ignore[method-assign]

    with pytest.raises(MPCRecoveryRequired):
        await coordinator.shutdown_session(SESSION_ID)


@pytest.mark.asyncio
async def test_failed_party_compute_waits_for_all_parties_before_cleanup():
    from backend.mpc.distributed_coordinator import DistributedCoordinator
    from backend.mpc.exceptions import MPCExecutionFailed

    events: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        party_id = int(request.url.host[-1])
        if request.url.path.endswith("/compute"):
            events.append(f"compute-{party_id}")
            if party_id == 1:
                return httpx.Response(502)
            return httpx.Response(
                200,
                json={
                    "aggregate_sum": 180000,
                    "average_salary": 60000.0,
                    "session_id": SESSION_ID,
                    "party_id": party_id,
                    "parties_count": 3,
                    "threshold": 1,
                },
            )
        if request.url.path.endswith("/shutdown"):
            events.append(f"shutdown-{party_id}")
            return httpx.Response(200, json={"status": "cleared"})
        return httpx.Response(404)

    coordinator = DistributedCoordinator(
        ["http://party0", "http://party1", "http://party2"],
        ["a", "b", "c"],
        require_tls=False,
    )
    coordinator._client = lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))  # type: ignore[method-assign]

    with pytest.raises(MPCExecutionFailed):
        await coordinator.execute_protocol(SESSION_ID, expires_at=int(time.time()) + 60)

    first_shutdown = next(index for index, event in enumerate(events) if event.startswith("shutdown-"))
    assert all(f"compute-{party_id}" in events[:first_shutdown] for party_id in range(3))
    assert {event for event in events if event.startswith("shutdown-")} == {
        "shutdown-0", "shutdown-1", "shutdown-2"
    }


@pytest.mark.asyncio
async def test_expiration_sweeper_purges_private_party_memory(party_module):
    from backend.mpc.lifecycle import PartyLifecycle, PartyState
    from backend.mpc.party_service import PartySession

    session = PartySession(
        lifecycle=PartyLifecycle(party_id=0, session_id=SESSION_ID),
        expires_at=10,
        private_input=987654,
    )
    session.lifecycle.mark_input_submitted()
    session.lifecycle.transition(PartyState.WAITING_FOR_PARTICIPANTS)
    party_module._sessions[SESSION_ID] = session

    removed = await party_module._cleanup_expired_sessions(now=11)

    assert removed == 1
    assert SESSION_ID not in party_module._sessions
    assert session.private_input is None
    assert session.computation_result is None
    assert party_module._state_store.get(SESSION_ID) is None


@pytest.mark.asyncio
async def test_mpyc_timeout_kills_and_drains_subprocess_pipes(party_module, monkeypatch):
    import asyncio

    class FakeProcess:
        def __init__(self):
            self.stdin = object()
            self.returncode = None
            self.killed = asyncio.Event()
            self.communicate_calls = 0

        async def communicate(self, _input=None):
            self.communicate_calls += 1
            await self.killed.wait()
            self.returncode = -9
            return b"", b""

        def kill(self):
            self.killed.set()

    process = FakeProcess()

    async def create_process(*_args, **_kwargs):
        return process

    monkeypatch.setattr(party_module.asyncio, "create_subprocess_exec", create_process)
    monkeypatch.setattr(party_module, "MPC_TIMEOUT_SECONDS", 0.01)

    with pytest.raises(TimeoutError, match="timed out"):
        await party_module._run_mpyc_computation(50000)

    assert process.returncode == -9
    assert process.communicate_calls == 1
