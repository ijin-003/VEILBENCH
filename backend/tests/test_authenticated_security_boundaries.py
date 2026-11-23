"""Authenticated negative-path tests using disposable SQLite accounts only.

No requests reach Render or Neon. ASGI routes and the party's durable replay
guard are exercised using synthetic accounts, sessions and salaries.
"""
import importlib.util
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.main import app
from backend.models import Base, BenchmarkSession
from backend.models.account import Account, LoginSession
from backend.security.accounts import digest, hash_password
from backend.security.tokens import issue_founder_token
from backend.services.database import get_database_session
from backend.config import settings


@pytest.mark.asyncio
async def test_authenticated_roles_invitations_and_expiration(tmp_path, monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///" + str(tmp_path / "auth-negative.sqlite"))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def session_override():
        async with factory() as db:
            yield db

    app.dependency_overrides[get_database_session] = session_override
    monkeypatch.setattr(settings, "MPC_FOUNDER_TOKEN_SECRET_0", "synthetic-founder-signing-secret")
    now = int(time.time())
    async with factory() as db:
        db.add_all([
            BenchmarkSession(
                id="current-test", state="created",
                created_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
                submitted_party_ids=[],
            ),
            BenchmarkSession(
                id="expired-test", state="created",
                created_at=datetime.now(timezone.utc) - timedelta(hours=2),
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=2),
                submitted_party_ids=[],
            ),
        ])
        await db.flush()
        db.add_all([
            Account(username="auditadmin", role="admin", password_hash=hash_password("synthetic-admin-password")),
            Account(
                username="auditfounder", role="participant",
                password_hash=hash_password("synthetic-founder-password"),
                benchmark_id="current-test", party_id=0,
            ),
            Account(
                username="auditinvite", role="participant",
                invitation_hash=digest("synthetic-invitation-000001"),
                invitation_expiry=now + 600, benchmark_id="current-test", party_id=1,
            ),
            Account(
                username="expiredinvite", role="participant",
                invitation_hash=digest("synthetic-invitation-000002"),
                invitation_expiry=now - 2, benchmark_id="expired-test", party_id=0,
            ),
        ])
        await db.flush()
        db.add_all([
            LoginSession(token_hash=digest("synthetic-admin-token"), username="auditadmin", expires_at=now + 300),
            LoginSession(token_hash=digest("synthetic-founder-token"), username="auditfounder", expires_at=now + 300),
            LoginSession(token_hash=digest("synthetic-expired-token"), username="auditadmin", expires_at=now - 1),
        ])
        await db.commit()

    admin = {"Authorization": "Bearer synthetic-admin-token"}
    founder = {"Authorization": "Bearer synthetic-founder-token"}
    expired = {"Authorization": "Bearer synthetic-expired-token"}
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            # Founder cannot use admin endpoints even when a valid login is supplied.
            for method, path, body in [
                ("POST", "/api/v1/sessions", {}),
                ("POST", "/api/v1/accounts/invitations",
                 {"username": "syntheticnew", "session_id": "current-test", "party_id": 2}),
                ("GET", "/api/v1/sessions/current-test", None),
            ]:
                response = await client.request(method, path, headers=founder, json=body)
                assert response.status_code == 403, (path, response.text)

            assert (await client.get("/api/v1/accounts/assignment", headers=admin)).status_code == 403
            assert (await client.get("/api/v1/accounts/assignment", headers=expired)).status_code == 401
            assignment = await client.get("/api/v1/accounts/assignment", headers=founder)
            assert assignment.status_code == 200
            assert assignment.json()["party_id"] == 0
            assert "capability" in assignment.json()

            valid_activation = {
                "username": "auditinvite",
                "password": "synthetic-new-password",
                "invitation": "synthetic-invitation-000001",
            }
            assert (await client.post("/api/v1/accounts/activate", json=valid_activation)).status_code == 200
            assert (await client.post("/api/v1/accounts/activate", json=valid_activation)).status_code == 400
            assert (await client.post("/api/v1/accounts/activate", json={
                "username": "expiredinvite", "password": "synthetic-new-password",
                "invitation": "synthetic-invitation-000002",
            })).status_code == 400

            # Expired benchmark refuses new founder capability even with a live login.
            async with factory() as db:
                benchmark = await db.get(BenchmarkSession, "current-test")
                benchmark.expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
                await db.commit()
            assert (await client.get("/api/v1/accounts/assignment", headers=founder)).status_code == 410

            assert (await client.post("/api/v1/accounts/logout", headers=founder)).status_code == 200
            assert (await client.get("/api/v1/accounts/assignment", headers=founder)).status_code == 401
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_founder_capability_scoping_and_replay_after_party_reload(tmp_path, monkeypatch):
    monkeypatch.setenv("MPC_PARTY_ID", "0")
    monkeypatch.setenv("MPC_PARTIES_COUNT", "3")
    monkeypatch.setenv("MPC_ENABLE_TLS", "false")
    monkeypatch.setenv("MPC_COORDINATOR_TOKEN", "synthetic-control-token")
    monkeypatch.setenv("MPC_FOUNDER_TOKEN_SECRET", "synthetic-party-secret")
    monkeypatch.setenv("MPC_PARTY_STATE_DB_PATH", str(tmp_path / "party-replay.sqlite"))

    def load_party(suffix):
        name = f"synthetic_party_security_{suffix}"
        spec = importlib.util.spec_from_file_location(name, Path("backend/mpc/party_service.py"))
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        return module

    party = load_party("first")
    exp = int(time.time()) + 600
    capability = issue_founder_token("synthetic-party-secret", "synthetic-session", 0, exp)
    expired = issue_founder_token("synthetic-party-secret", "synthetic-session", 0, int(time.time()) - 1)
    wrong_party = issue_founder_token("synthetic-party-secret", "synthetic-session", 1, exp)
    wrong_session = issue_founder_token("synthetic-party-secret", "other-session", 0, exp)
    altered = ("A" if capability[0] != "A" else "B") + capability[1:]
    url = "/sessions/synthetic-session/input"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=party.app), base_url="http://test") as client:
        for bad_token in [expired, wrong_party, wrong_session, altered]:
            response = await client.post(url, json={"salary": 50000},
                                         headers={"Authorization": "Bearer " + bad_token})
            assert response.status_code == 403
            assert "50000" not in response.text

        ok = await client.post(url, json={"salary": 50000},
                               headers={"Authorization": "Bearer " + capability})
        assert ok.status_code == 200
        again = await client.post(url, json={"salary": 70000},
                                  headers={"Authorization": "Bearer " + capability})
        assert again.status_code == 409
        assert "70000" not in again.text

    # Reloading the party module resets volatile memory but preserves the
    # same on-disk replay guard. No second salary may be accepted.
    party._sessions["synthetic-session"].private_input = None
    party_reloaded = load_party("second")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=party_reloaded.app), base_url="http://test") as client:
        replay = await client.post(url, json={"salary": 90000},
                                   headers={"Authorization": "Bearer " + capability})
        assert replay.status_code == 409
        assert "90000" not in replay.text
