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
