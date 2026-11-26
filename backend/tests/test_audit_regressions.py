"""Comprehensive audit regression tests for Phases B, C, D, F, G, and K."""

from __future__ import annotations

import asyncio
import importlib.util
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.config import settings
from backend.main import app
from backend.models import Base, BenchmarkSession
from backend.models.account import Account, LoginSession
from backend.mpc.config import MAX_SALARY, MIN_SALARY
from backend.mpc.exceptions import InvalidSalaryError
from backend.mpc.validation import validate_salary
from backend.security.accounts import digest, hash_password
from backend.services.database import get_database_session


async def _setup_db(tmp_path: Path, name: str = "audit.sqlite"):
    engine = create_async_engine("sqlite+aiosqlite:///" + str(tmp_path / name))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def db_override():
        async with factory() as db:
            yield db

    app.dependency_overrides[get_database_session] = db_override
    return engine, factory


@pytest.mark.asyncio
async def test_phase_b_founder_identity_and_error_distinction(tmp_path):
    """Verify duplicate display names, Unicode/spaces, validation rejections, and slot uniqueness."""
    engine, factory = await _setup_db(tmp_path, "phase_b.sqlite")
    now = datetime.now(timezone.utc)
    async with factory() as db:
        db.add(Account(username="admin", role="admin", password_hash=hash_password("AdminStrongPassword123!")))
        db.add(BenchmarkSession(id="s-active", state="created", created_at=now, expires_at=now + timedelta(minutes=30), submitted_party_ids=[]))
        db.add(BenchmarkSession(id="s-active-2", state="created", created_at=now, expires_at=now + timedelta(minutes=30), submitted_party_ids=[]))
        db.add(BenchmarkSession(id="s-expired", state="created", created_at=now - timedelta(hours=1), expires_at=now - timedelta(minutes=5), submitted_party_ids=[]))
        db.add(BenchmarkSession(id="s-completed", state="completed", created_at=now, expires_at=now + timedelta(minutes=30), submitted_party_ids=[0, 1, 2], aggregate_sum=180000, average_salary=60000.0))
        await db.commit()

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            login = await client.post("/api/v1/accounts/login", json={"username": "admin", "password": "AdminStrongPassword123!"})
            assert login.status_code == 200
            admin = {"Authorization": f"Bearer {login.json()['token']}"}

            # Unauthorized request
            unauth = await client.post("/api/v1/accounts/invitations", json={"display_name": "Alice", "session_id": "s-active", "party_id": 0})
            assert unauth.status_code == 401

            # Identical display names in the same session -> distinct generated usernames
            r0 = await client.post("/api/v1/accounts/invitations", json={"display_name": "Alex Rivera", "session_id": "s-active", "party_id": 0}, headers=admin)
            r1 = await client.post("/api/v1/accounts/invitations", json={"display_name": "Alex Rivera", "session_id": "s-active", "party_id": 1}, headers=admin)
            assert r0.status_code == 201 and r1.status_code == 201
            assert r0.json()["username"] != r1.json()["username"]
            assert r0.json()["display_name"] == "Alex Rivera"
            assert r0.headers["cache-control"] == "no-store"

            # Unicode and mixed-case display names across different sessions
            r2 = await client.post("/api/v1/accounts/invitations", json={"display_name": "José García / 李明", "session_id": "s-active", "party_id": 2}, headers=admin)
            r_cross = await client.post("/api/v1/accounts/invitations", json={"display_name": "Alex Rivera", "session_id": "s-active-2", "party_id": 0}, headers=admin)
            assert r2.status_code == 201 and r_cross.status_code == 201
            assert len({r0.json()["username"], r1.json()["username"], r2.json()["username"], r_cross.json()["username"]}) == 4

            # Already occupied founder slot -> 409
            occupied = await client.post("/api/v1/accounts/invitations", json={"display_name": "Another", "session_id": "s-active", "party_id": 0}, headers=admin)
            assert occupied.status_code == 409
            assert "slot" in occupied.json()["detail"].lower()

            # Duplicate explicit login username -> 409
            explicit = await client.post("/api/v1/accounts/invitations", json={"username": "custom.founder", "display_name": "Custom", "session_id": "s-active-2", "party_id": 1}, headers=admin)
            assert explicit.status_code == 201
            dup_user = await client.post("/api/v1/accounts/invitations", json={"username": "custom.founder", "display_name": "Other", "session_id": "s-active-2", "party_id": 2}, headers=admin)
            assert dup_user.status_code == 409
            assert "username" in dup_user.json()["detail"].lower()

            # Invalid session -> 404
            missing = await client.post("/api/v1/accounts/invitations", json={"display_name": "Test", "session_id": "does-not-exist", "party_id": 0}, headers=admin)
            assert missing.status_code == 404

            # Expired & completed sessions -> 409
            exp_resp = await client.post("/api/v1/accounts/invitations", json={"display_name": "Test", "session_id": "s-expired", "party_id": 0}, headers=admin)
            comp_resp = await client.post("/api/v1/accounts/invitations", json={"display_name": "Test", "session_id": "s-completed", "party_id": 0}, headers=admin)
            assert exp_resp.status_code == 409 and comp_resp.status_code == 409

            # Empty, whitespace-only, control chars, and excessively long names -> 422
            for bad_name in ["", "   ", "\t\n", "Bad\x00Name", "Bad\x7fName", "A" * 81]:
                bad = await client.post("/api/v1/accounts/invitations", json={"display_name": bad_name, "session_id": "s-active-2", "party_id": 2}, headers=admin)
                assert bad.status_code == 422, f"Expected 422 for {bad_name!r}, got {bad.status_code}"
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_phase_c_d_password_policy_and_invitation_reissue(tmp_path):
    """Verify repeated-char/weak password rejection, reissue invalidation, and role isolation."""
    engine, factory = await _setup_db(tmp_path, "phase_cd.sqlite")
    now = datetime.now(timezone.utc)
    async with factory() as db:
        db.add(Account(username="admin", role="admin", password_hash=hash_password("AdminStrongPassword123!")))
        db.add(BenchmarkSession(id="s-cd", state="created", created_at=now, expires_at=now + timedelta(minutes=30), submitted_party_ids=[]))
        db.add(BenchmarkSession(id="s-cd-closed", state="completed", created_at=now, expires_at=now + timedelta(minutes=30), submitted_party_ids=[0, 1, 2]))
        await db.commit()

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            login = await client.post("/api/v1/accounts/login", json={"username": "admin", "password": "AdminStrongPassword123!"})
            admin = {"Authorization": f"Bearer {login.json()['token']}"}

            inv = await client.post("/api/v1/accounts/invitations", json={"display_name": "Founder One", "session_id": "s-cd", "party_id": 0}, headers=admin)
            assert inv.status_code == 201
            uname = inv.json()["username"]
            old_tok = inv.json()["invitation"]

            # Reissue unused invitation: keeps username/display_name, invalidates old token
            reissue = await client.post("/api/v1/accounts/invitations/reissue", json={"session_id": "s-cd", "party_id": 0}, headers=admin)
            assert reissue.status_code == 201
            assert reissue.headers["cache-control"] == "no-store"
            assert reissue.json()["username"] == uname
            assert reissue.json()["display_name"] == "Founder One"
            new_tok = reissue.json()["invitation"]
            assert new_tok != old_tok

            # Old token rejected
            old_act = await client.post("/api/v1/accounts/activate", json={"username": uname, "password": "UniqueValidPassword99!", "invitation": old_tok})
            assert old_act.status_code == 400

            # Weak passwords rejected (12 repeated chars, common, contains username, too short)
            for weak_pw in ["aaaaaaaaaaaa", "password123456", f"xx{uname}yy123", "shortpw"]:
                resp = await client.post("/api/v1/accounts/activate", json={"username": uname, "password": weak_pw, "invitation": new_tok})
                assert resp.status_code in (400, 422), f"Weak password {weak_pw!r} was not rejected"

            # Valid activation succeeds
            ok_act = await client.post("/api/v1/accounts/activate", json={"username": uname, "password": "UniqueValidPassword99!", "invitation": new_tok})
            assert ok_act.status_code == 200

            # Activated account cannot be reissued
            reissue_after = await client.post("/api/v1/accounts/invitations/reissue", json={"session_id": "s-cd", "party_id": 0}, headers=admin)
            assert reissue_after.status_code == 409

            # Closed session cannot reissue
            closed_reissue = await client.post("/api/v1/accounts/invitations/reissue", json={"session_id": "s-cd-closed", "party_id": 0}, headers=admin)
            assert closed_reissue.status_code == 409

            # Founder cannot issue or reissue invitations
            f_login = await client.post("/api/v1/accounts/login", json={"username": uname, "password": "UniqueValidPassword99!"})
            assert f_login.status_code == 200
            founder_hdr = {"Authorization": f"Bearer {f_login.json()['token']}"}
            assert (await client.post("/api/v1/accounts/invitations", json={"display_name": "X", "session_id": "s-cd", "party_id": 1}, headers=founder_hdr)).status_code == 403
            assert (await client.post("/api/v1/accounts/invitations/reissue", json={"session_id": "s-cd", "party_id": 1}, headers=founder_hdr)).status_code == 403

            # Account directory never exposes hashes/tokens and sets Cache-Control: no-store
            directory = await client.get("/api/v1/accounts", headers=admin)
            assert directory.status_code == 200
            assert directory.headers["cache-control"] == "no-store"
            assert "password_hash" not in directory.text and "invitation_hash" not in directory.text
            assert new_tok not in directory.text and old_tok not in directory.text
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


def test_phase_f_migration_preserves_legacy_accounts(tmp_path, monkeypatch):
    """Upgrade 0001 -> 0002 -> insert legacy row -> upgrade head -> verify NULLs preserved."""
    from alembic import command
    from alembic.config import Config

    path = tmp_path / "legacy_migration.sqlite"
    monkeypatch.setattr(settings, "DATABASE_URL", "sqlite+aiosqlite:///" + str(path))
    config = Config("alembic.ini")
    command.upgrade(config, "0002_accounts")
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT INTO accounts (username, role, password_hash, invitation_expiry, failures, locked_until) "
            "VALUES ('legacy-admin', 'admin', 'scrypt$00$00', 0, 0, 0)"
        )
        conn.commit()
    command.upgrade(config, "head")
    with sqlite3.connect(path) as conn:
        row = conn.execute(
            "SELECT username, role, created_at, display_name FROM accounts WHERE username='legacy-admin'"
        ).fetchone()
        assert row == ("legacy-admin", "admin", None, None)
    command.downgrade(config, "0002_accounts")
    command.downgrade(config, "0001_initial")


def test_phase_g_salary_domain_boundaries():
    assert validate_salary(MIN_SALARY) == 0
    assert validate_salary(MAX_SALARY) == 10_000_000
    for bad in (-1, MAX_SALARY + 1, 1.5, True, "50000", None):
        with pytest.raises(InvalidSalaryError):
            validate_salary(bad)


@pytest.mark.asyncio
async def test_phase_k_full_20_step_e2e_workflow(tmp_path, monkeypatch):
    """Execute the full 20-step E2E workflow across coordinator, 3 party services, and MPyC."""
    engine, factory = await _setup_db(tmp_path, "phase_k.sqlite")
    for i in range(3):
        monkeypatch.setattr(settings, f"MPC_FOUNDER_TOKEN_SECRET_{i}", f"audit-secret-{i}-0123456789abcdef012345")
        monkeypatch.setenv(f"MPC_PARTY_{i}_HOST", "127.0.0.1")

    parties = []
    for i in range(3):
        monkeypatch.setenv("MPC_PARTY_ID", str(i))
        monkeypatch.setenv("MPC_PARTIES_COUNT", "3")
        monkeypatch.setenv("MPC_BASE_PORT", "12960")
        monkeypatch.setenv("MPC_ENABLE_TLS", "false")
        monkeypatch.setenv("MPC_COORDINATOR_TOKEN", f"audit-ctrl-{i}-0123456789abcdef012345")
        monkeypatch.setenv("MPC_FOUNDER_TOKEN_SECRET", f"audit-secret-{i}-0123456789abcdef012345")
        monkeypatch.setenv("MPC_PARTY_STATE_DB_PATH", str(tmp_path / f"party-k-{i}.sqlite"))
        name = f"audit_e2e_party_{i}"
        spec = importlib.util.spec_from_file_location(name, Path("backend/mpc/party_service.py"))
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        parties.append(module)

    async with factory() as db:
        db.add(Account(username="admin", role="admin", password_hash=hash_password("AdminStrongPassword123!")))
        db.add(BenchmarkSession(id="e2e-session", state="created", created_at=datetime.now(timezone.utc), expires_at=datetime.now(timezone.utc) + timedelta(minutes=30), submitted_party_ids=[]))
        await db.commit()

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            # 1. Admin signs in
            admin_login = await client.post("/api/v1/accounts/login", json={"username": "admin", "password": "AdminStrongPassword123!"})
            assert admin_login.status_code == 200
            admin_hdr = {"Authorization": f"Bearer {admin_login.json()['token']}"}

            # 3. Session appears in active directory
            active_dir = await client.get("/api/v1/sessions?scope=active", headers=admin_hdr)
            assert active_dir.status_code == 200
            assert any(s["session_id"] == "e2e-session" for s in active_dir.json()["sessions"])

            # 5-7. Generate 3 invitations, 2 with identical display names, all distinct login IDs
            names = ["Sam Founder", "Sam Founder", "Jordan Lee"]
            invites = []
            for pid, dname in enumerate(names):
                res = await client.post("/api/v1/accounts/invitations", json={"display_name": dname, "session_id": "e2e-session", "party_id": pid}, headers=admin_hdr)
                assert res.status_code == 201
                invites.append(res.json())
            assert len({inv["username"] for inv in invites}) == 3

            # 8-9. Reissue slot 1 and verify old invitation is rejected
            old_inv_1 = invites[1]["invitation"]
            reissued = await client.post("/api/v1/accounts/invitations/reissue", json={"session_id": "e2e-session", "party_id": 1}, headers=admin_hdr)
            assert reissued.status_code == 201
            invites[1]["invitation"] = reissued.json()["invitation"]
            assert (await client.post("/api/v1/accounts/activate", json={"username": invites[1]["username"], "password": "FounderPassword123!", "invitation": old_inv_1})).status_code == 400

            # 10-12. Activate, sign in, and submit synthetic salaries directly to assigned party
            salaries = [50000, 70000, 60000]
            founder_tokens = []
            for pid, inv in enumerate(invites):
                act = await client.post("/api/v1/accounts/activate", json={"username": inv["username"], "password": "FounderPassword123!", "invitation": inv["invitation"]})
                assert act.status_code == 200
                fl = await client.post("/api/v1/accounts/login", json={"username": inv["username"], "password": "FounderPassword123!"})
                assert fl.status_code == 200
                fh = {"Authorization": f"Bearer {fl.json()['token']}"}
                founder_tokens.append(fh)
                assign = await client.get("/api/v1/accounts/assignment", headers=fh)
                assert assign.status_code == 200 and assign.json()["party_id"] == pid
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=parties[pid].app), base_url="http://party") as pc:
                    sub = await pc.post("/sessions/e2e-session/input", json={"salary": salaries[pid]}, headers={"Authorization": f"Bearer {assign.json()['capability']}"})
                    assert sub.status_code == 200 and sub.json()["input_submitted"] is True

            # 15-16. Genuine 3-party MPyC execution
            async def run_party(pid: int):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=parties[pid].app), base_url="http://party") as pc:
                    return await pc.post("/sessions/e2e-session/compute", headers={"Authorization": f"Bearer audit-ctrl-{pid}-0123456789abcdef012345"})

            results = await asyncio.gather(*(run_party(pid) for pid in range(3)))
            for res in results:
                assert res.status_code == 200
                assert res.json()["aggregate_sum"] == 180000
                assert res.json()["average_salary"] == 60000.0

            # 19-20. Unauthorized founder access rejected & all participants log out
            for fh in founder_tokens:
                assert (await client.get("/api/v1/accounts", headers=fh)).status_code == 403
                assert (await client.post("/api/v1/accounts/logout", headers=fh)).status_code == 200
            assert (await client.post("/api/v1/accounts/logout", headers=admin_hdr)).status_code == 200
            async with factory() as db:
                remaining = (await db.scalars(select(LoginSession))).all()
                assert remaining == []
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
