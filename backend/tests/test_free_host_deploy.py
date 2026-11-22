"""Contract checks for the optional one-port $0 academic demo deployment."""
import os
from pathlib import Path

import httpx
import pytest


def test_render_blueprint_is_exactly_one_free_web_service():
    root = Path(__file__).resolve().parents[2]
    blueprint = (root / "render.yaml").read_text()
    assert blueprint.count("- type: web") == 1
    assert "plan: free" in blueprint and "runtime: docker" in blueprint
    assert "dockerfilePath: ./infrastructure/Dockerfile.free" in blueprint
    for key in ("DATABASE_URL", "FRONTEND_PUBLIC_URL", "VEILBENCH_INITIAL_ADMIN_USERNAME", "VEILBENCH_INITIAL_ADMIN_PASSWORD"):
        assert f"key: {key}" in blueprint
    assert "CHANGE_ME" not in blueprint


def test_free_host_configuration_requires_explicit_secrets(monkeypatch):
    from scripts.start_free_host import configure
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "veilbench-poc.onrender.com")
    monkeypatch.setenv("PORT", "10000")
    monkeypatch.setenv("FRONTEND_PUBLIC_URL", "https://veilbench.vercel.app")
    monkeypatch.setenv("DATABASE_URL", "postgresql://demo:password@db.example.com/db?sslmode=require")
    for i in range(3):
        monkeypatch.setenv(f"MPC_NODE{i}_TOKEN", f"control{i}" * 8)
        monkeypatch.setenv(f"MPC_FOUNDER_TOKEN_SECRET_{i}", f"founder{i}" * 8)
    monkeypatch.delenv("COORDINATOR_ADMIN_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="COORDINATOR_ADMIN_TOKEN"):
        configure()


def test_free_host_urls_and_neon_connection(monkeypatch):
    from scripts.start_free_host import configure
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "veilbench-poc.onrender.com")
    monkeypatch.setenv("PORT", "10000")
    monkeypatch.setenv("FRONTEND_PUBLIC_URL", "https://veilbench.vercel.app")
    monkeypatch.setenv("DATABASE_URL", "postgresql://demo:password@db.example.com/db?sslmode=require")
    monkeypatch.setenv("COORDINATOR_ADMIN_TOKEN", "a" * 48)
    for i in range(3):
        monkeypatch.setenv(f"MPC_NODE{i}_TOKEN", f"control{i}" * 8)
        monkeypatch.setenv(f"MPC_FOUNDER_TOKEN_SECRET_{i}", f"founder{i}" * 8)
    assert configure() == 10000
    assert os.environ["DATABASE_URL"] == "postgresql+asyncpg://demo:password@db.example.com/db?ssl=require"
    assert os.environ["MPC_NODE0_URL"] == "http://127.0.0.1:10000/party/0"
    assert os.environ["MPC_PARTY_PUBLIC_URLS"] == ",".join(f"https://veilbench-poc.onrender.com/party/{i}" for i in range(3))
    assert os.environ["MPC_REQUIRE_TLS"] == "false"


@pytest.mark.asyncio
async def test_free_host_mounts_three_distinct_parties(monkeypatch, tmp_path):
    from scripts.start_free_host import configure
    monkeypatch.chdir(Path(__file__).resolve().parents[2])
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "veilbench-poc.onrender.com")
    monkeypatch.setenv("FRONTEND_PUBLIC_URL", "https://veilbench.vercel.app")
    monkeypatch.setenv("DATABASE_URL", "postgresql://demo:password@db.example.com/db?sslmode=require")
    monkeypatch.setenv("COORDINATOR_ADMIN_TOKEN", "a" * 48)
    for i in range(3):
        monkeypatch.setenv(f"MPC_NODE{i}_TOKEN", f"control{i}" * 8)
        monkeypatch.setenv(f"MPC_FOUNDER_TOKEN_SECRET_{i}", f"founder{i}" * 8)
    configure()
    from backend.ops.free_host_app import create_app
    app = create_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        for i in range(3):
            r = await client.get(f"/party/{i}/health")
            assert r.status_code == 200 and r.json()["party_id"] == i
            assert r.json()["mpyc_tls_enabled"] is False
        assert (await client.get("/health")).json()["service"] == "VEILBENCH"
        assert (await client.get("/party/3/health")).status_code == 404
