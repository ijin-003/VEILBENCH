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


def _make_party_app(party_id: int = 0):
    os.environ.update(
        {
            "MPC_PARTY_ID": str(party_id),
            "MPC_PARTIES_COUNT": "3",
            "MPC_COORDINATOR_TOKEN": CONTROL_TOKEN,
            "MPC_FOUNDER_TOKEN_SECRET": FOUNDER_SECRET,
            "MPC_ENABLE_TLS": "false",
            "MPC_BASE_PORT": "11365",
        }
    )
    import backend.mpc.party_service as party_service

    return importlib.reload(party_service)


@pytest.fixture
def party_module():
    return _make_party_app()


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
