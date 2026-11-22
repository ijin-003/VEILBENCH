"""Exercise account isolation through the real HTTP routes and SQL storage."""
import time
import asyncio
import importlib.util
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.main import app
from backend.models import Base, BenchmarkSession
from backend.models.account import Account, LoginSession
from backend.security.accounts import hash_password, digest
from backend.services.database import get_database_session
from backend.config import settings
from backend.security.tokens import verify_founder_token, FounderTokenError


@pytest.mark.asyncio
async def test_account_lifecycle_and_role_isolation(tmp_path, monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///" + str(tmp_path / "accounts.sqlite"))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async def db_override():
        async with factory() as db:
            yield db
    app.dependency_overrides[get_database_session] = db_override
    for i in range(3):
        monkeypatch.setattr(settings, f"MPC_FOUNDER_TOKEN_SECRET_{i}", f"test-signing-secret-{i}")
        monkeypatch.setenv(f"MPC_PARTY_{i}_HOST", "127.0.0.1")
    # Separate party application instances, private stores and real MPC workers.
    parties = []
    for i in range(3):
        monkeypatch.setenv("MPC_PARTY_ID", str(i))
        monkeypatch.setenv("MPC_PARTIES_COUNT", "3")
        monkeypatch.setenv("MPC_BASE_PORT", "12940")
        monkeypatch.setenv("MPC_ENABLE_TLS", "false")
        monkeypatch.setenv("MPC_COORDINATOR_TOKEN", f"test-control-{i}")
        monkeypatch.setenv("MPC_FOUNDER_TOKEN_SECRET", f"test-signing-secret-{i}")
        monkeypatch.setenv("MPC_PARTY_STATE_DB_PATH", str(tmp_path / f"party-{i}.sqlite"))
        name = f"account_test_party_{i}"
        spec = importlib.util.spec_from_file_location(name, Path("backend/mpc/party_service.py"))
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        parties.append(module)
    async with factory() as db:
        db.add(Account(username="admin", role="admin", password_hash=hash_password("test-admin-password")))
        db.add(BenchmarkSession(id="test-session", state="created", created_at=datetime.now(timezone.utc), expires_at=datetime.now(timezone.utc) + timedelta(minutes=30), submitted_party_ids=[]))
        await db.commit()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/accounts/login", json={"username":"admin", "password":"test-admin-password"})
            assert response.status_code == 200
            admin = {"Authorization": "Bearer " + response.json()["token"]}
            assert response.headers["cache-control"] == "no-store"
            assert (await client.post("/api/v1/accounts/invitations", json={"username":"outsider", "session_id":"test-session", "party_id":0})).status_code == 401
            for party in range(3):
                name = f"participant-{party}"
                body = {"username":name, "session_id":"test-session", "party_id":party}
                invite = await client.post("/api/v1/accounts/invitations", json=body, headers=admin)
                assert invite.status_code == 201
                assert (await client.post("/api/v1/accounts/invitations", json=body, headers=admin)).status_code == 409
                activation = {"username":name, "password":"participant-password", "invitation":invite.json()["invitation"]}
                assert (await client.post("/api/v1/accounts/activate", json={**activation, "invitation":"incorrect-invitation-code"})).status_code == 400
                assert (await client.post("/api/v1/accounts/activate", json=activation)).status_code == 200
                assert (await client.post("/api/v1/accounts/activate", json=activation)).status_code == 400
                member = await client.post("/api/v1/accounts/login", json={"username":name,"password":"participant-password"})
                assert member.status_code == 200
                token = member.json()["token"]
                headers = {"Authorization": "Bearer " + token}
                own = await client.get("/api/v1/accounts/assignment", headers=headers)
                assert own.status_code == 200 and own.json()["party_id"] == party
                verify_founder_token(own.json()["capability"], settings.founder_secrets[party], "test-session", party)
                with pytest.raises(FounderTokenError):
                    verify_founder_token(own.json()["capability"], settings.founder_secrets[(party + 1) % 3], "test-session", (party + 1) % 3)
                assert "salary" not in own.text
                founder_headers = {"Authorization": "Bearer " + own.json()["capability"]}
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=parties[party].app), base_url="http://party") as party_client:
                    submitted = await party_client.post("/sessions/test-session/input", json={"salary": [50000, 70000, 60000][party]}, headers=founder_headers)
                    assert submitted.status_code == 200 and submitted.json()["party_id"] == party
                    assert (await party_client.post("/sessions/test-session/input", json={"salary": 1}, headers=founder_headers)).status_code == 409
                    assert (await party_client.get("/sessions/test-session/status", headers=founder_headers)).status_code == 403
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=parties[(party + 1) % 3].app), base_url="http://wrong-party") as wrong_party:
                    assert (await wrong_party.post("/sessions/test-session/input", json={"salary": 1}, headers=founder_headers)).status_code == 403
                assert (await client.post("/api/v1/accounts/invitations", json=body, headers=headers)).status_code == 403
                assert (await client.post("/api/v1/sessions", json={}, headers=headers)).status_code == 403
                assert (await client.get("/api/v1/sessions/test-session", headers=headers)).status_code == 403
                assert (await client.post("/api/v1/accounts/logout", headers=headers)).status_code == 200
                assert (await client.get("/api/v1/accounts/assignment", headers=headers)).status_code == 401
                async with factory() as db:
                    assert await db.get(LoginSession, digest(token)) is None
                    account = await db.get(Account, name)
                    assert account.password_hash != "participant-password" and account.invitation_hash is None
            async def compute(party):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=parties[party].app), base_url="http://party") as party_client:
                    response = await party_client.post("/sessions/test-session/compute", headers={"Authorization": f"Bearer test-control-{party}"})
                    assert response.status_code == 200
                    assert response.json()["aggregate_sum"] == 180000
                    assert response.json()["average_salary"] == 60000
                    assert parties[party]._sessions["test-session"].private_input is None
            await asyncio.gather(*(compute(party) for party in range(3)))
            # Wrong password attempts lock the account; expiry revokes access.
            for _ in range(5):
                assert (await client.post("/api/v1/accounts/login", json={"username":"participant-0","password":"wrong-password"})).status_code == 401
            assert (await client.post("/api/v1/accounts/login", json={"username":"participant-0","password":"participant-password"})).status_code == 401
            async with factory() as db:
                row = await db.get(LoginSession, digest(admin["Authorization"][7:]))
                row.expires_at = int(time.time()) - 1
                await db.commit()
            assert (await client.get("/api/v1/accounts/assignment", headers=admin)).status_code == 401
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


def test_account_migration_upgrade_and_downgrade(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    import sqlite3
    path = tmp_path / "migration.sqlite"
    monkeypatch.setattr(settings, "DATABASE_URL", "sqlite+aiosqlite:///" + str(path))
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    with sqlite3.connect(path) as connection:
        names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"accounts", "login_sessions", "benchmark_sessions"} <= names
    command.downgrade(config, "0001_initial")
    with sqlite3.connect(path) as connection:
        names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "accounts" not in names and "benchmark_sessions" in names
