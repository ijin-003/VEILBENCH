import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["project"] == "VEILBENCH"
        assert data["status"] == "operational"


@pytest.mark.asyncio
async def test_health_check_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "VEILBENCH"
        assert "mpc_configuration" in data
        assert data["mpc_configuration"]["parties"] == 3
        assert data["mpc_configuration"]["threshold"] == 1
        assert data["mpc_configuration"]["honest_majority"] is True


@pytest.mark.asyncio
async def test_root_health_alias():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_liveness_endpoint_does_not_require_database():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_readiness_endpoint_fails_when_database_is_unavailable(monkeypatch):
    from backend.services.database import database

    monkeypatch.setattr(database, "session_factory", None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")
        assert response.status_code == 503


@pytest.mark.asyncio
async def test_api_readiness_route_is_registered():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")
        assert response.status_code == 503
