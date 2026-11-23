"""Read-only admin inventory: role isolation, expiry and secret non-disclosure."""
from datetime import datetime, timedelta, timezone
import time

import httpx
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.main import app
from backend.models import Base, BenchmarkSession
from backend.models.account import Account, LoginSession
from backend.security.accounts import digest
from backend.services.database import get_database_session
from backend.config import settings


@pytest.mark.asyncio
async def test_directories_are_admin_only_paginated_and_secret_free(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "COORDINATOR_ADMIN_TOKEN", "synthetic-control-only")
    engine = create_async_engine("sqlite+aiosqlite:///" + str(tmp_path / "directory.sqlite"))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def local_db():
        async with factory() as db:
            yield db

    now = datetime.now(timezone.utc)
    secret = "private-invitation-sentinel"
    async with factory() as db:
        db.add_all([
            Account(username="admin", role="admin", password_hash="password-hash-sentinel"),
            Account(username="founder1", role="participant", invitation_hash=secret, invitation_expiry=int(time.time())+600,
                    benchmark_id="active-session", party_id=0),
            Account(username="founder2", role="participant", password_hash="another-secret-password-hash",
                    benchmark_id="active-session", party_id=1),
        ])
        db.add_all([
            LoginSession(token_hash=digest("admin-token"), username="admin", expires_at=int(time.time()) + 3600),
            LoginSession(token_hash=digest("founder-token"), username="founder2", expires_at=int(time.time()) + 3600),
        ])
        db.add_all([
            BenchmarkSession(id="active-session", state="created", created_at=now,
                             expires_at=now + timedelta(minutes=30), submitted_party_ids=[0]),
            BenchmarkSession(id="completed-session", state="completed", created_at=now - timedelta(hours=1),
                             expires_at=now + timedelta(minutes=1), submitted_party_ids=[0, 1, 2],
                             aggregate_sum=180000, average_salary=60000),
            BenchmarkSession(id="expired-session", state="created", created_at=now - timedelta(hours=2),
                             expires_at=now - timedelta(seconds=1), submitted_party_ids=[]),
        ])
        await db.commit()
    app.dependency_overrides[get_database_session] = local_db
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            admin = {"Authorization": "Bearer admin-token"}
            founder = {"Authorization": "Bearer founder-token"}
            for path in ["/api/v1/accounts", "/api/v1/sessions", "/api/v1/sessions?scope=all"]:
                assert (await client.get(path)).status_code == 401
                assert (await client.get(path, headers=founder)).status_code == 403

            accounts = await client.get("/api/v1/accounts", headers=admin)
            assert accounts.status_code == 200
            assert accounts.headers["cache-control"] == "no-store"
            payload = accounts.json()
            assert payload["total"] == 3
            assert {row["username"] for row in payload["accounts"]} == {"admin", "founder1", "founder2"}
            assert {row["activation_status"] for row in payload["accounts"] if row["role"] == "participant"} == {"active", "invited"}
            for forbidden in ("password_hash", "invitation_hash", "token_hash", secret, "another-secret-password-hash", "salary"):
                assert forbidden not in accounts.text
            assert (await client.get("/api/v1/accounts?limit=1&offset=1", headers=admin)).json()["total"] == 3
            assert len((await client.get("/api/v1/accounts?limit=1&offset=1", headers=admin)).json()["accounts"]) == 1
            assert (await client.get("/api/v1/accounts?limit=101", headers=admin)).status_code == 422

            active = await client.get("/api/v1/sessions", headers=admin)
            assert active.status_code == 200
            assert active.headers["cache-control"] == "no-store"
            assert active.json()["total"] == 1
            assert [session["session_id"] for session in active.json()["sessions"]] == ["active-session"]
            assert active.json()["sessions"][0]["submitted_party_ids"] == [0]
            all_sessions = await client.get("/api/v1/sessions?scope=all", headers=admin)
            assert all_sessions.json()["total"] == 3
            assert {session["session_id"] for session in all_sessions.json()["sessions"]} == {
                "active-session", "completed-session", "expired-session",
            }
            assert "secret" not in all_sessions.text
            assert (await client.get("/api/v1/sessions?scope=unexpected", headers=admin)).status_code == 422
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
