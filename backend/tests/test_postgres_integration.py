"""Opt-in native PostgreSQL integration coverage for the audit release.

The workflow that enables this test creates an isolated PostgreSQL 16 service
named ``veilbench_audit`` on loopback.  The guard below deliberately refuses
any other database target so this test cannot be pointed at Render, Neon, or
an ordinary developer database by accident.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.config import settings
from backend.models import BenchmarkSession, SessionState
from backend.models.account import Account
from backend.mpc.exceptions import MPCExecutionFailed
from backend.security.accounts import hash_password
from backend.services.session_service import (
    SessionLifecycleError,
    compute_session,
    get_session,
    refresh_submission_state,
)

pytestmark = pytest.mark.asyncio

PARTY_HTTP_PORTS = (18310, 18311, 18312)
MPYC_PEER_PORT = 19310
SYNTHETIC_SALARIES = (50_000, 70_000, 60_000)
ADMIN_PASSWORD = "synthetic-audit-admin-password-only"
FOUNDER_PASSWORD = "synthetic-audit-founder-password-only"


def _integration_database_url() -> str:
    """Return only an explicitly named, loopback-only disposable database."""
    if os.environ.get("VEILBENCH_POSTGRES_INTEGRATION") != "1":
        pytest.skip("requires VEILBENCH_POSTGRES_INTEGRATION=1 and a disposable PostgreSQL service")
    url = os.environ.get("VEILBENCH_POSTGRES_TEST_DATABASE_URL", "")
    parsed = urlsplit(url)
    assert parsed.scheme == "postgresql+asyncpg", "test database must use asyncpg"
    assert parsed.hostname in {"127.0.0.1", "localhost", "::1"}, "database must be loopback only"
    assert parsed.path == "/veilbench_audit", "database must be the dedicated veilbench_audit database"
    return url


def _configure_test_runtime(monkeypatch: pytest.MonkeyPatch, database_url: str) -> None:
    """Configure only synthetic local endpoints and credentials for this test."""
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DATABASE_AUTO_CREATE", "false")
    monkeypatch.setenv("MPC_REQUIRE_TLS", "false")
    monkeypatch.setenv("FRONTEND_PUBLIC_URL", "http://127.0.0.1:3000")
    monkeypatch.setenv("MPC_PARTIES_COUNT", "3")
    monkeypatch.setenv("MPC_THRESHOLD", "1")
    monkeypatch.setenv("SESSION_TTL_SECONDS", "1800")
    monkeypatch.setenv("COORDINATOR_ADMIN_TOKEN", "synthetic-audit-coordinator-admin-credential")
    monkeypatch.setenv(
        "MPC_PARTY_PUBLIC_URLS",
        json.dumps([f"http://127.0.0.1:{port}" for port in PARTY_HTTP_PORTS]),
    )

    values: dict[str, object] = {
        "DATABASE_URL": database_url,
        "ENVIRONMENT": "development",
        "DATABASE_AUTO_CREATE": False,
        "MPC_REQUIRE_TLS": False,
        "FRONTEND_PUBLIC_URL": "http://127.0.0.1:3000",
        "MPC_PARTIES_COUNT": 3,
        "MPC_THRESHOLD": 1,
        "SESSION_TTL_SECONDS": 1800,
        "COORDINATOR_ADMIN_TOKEN": "synthetic-audit-coordinator-admin-credential",
        "MPC_PARTY_PUBLIC_URLS": [f"http://127.0.0.1:{port}" for port in PARTY_HTTP_PORTS],
    }
    for party_id, port in enumerate(PARTY_HTTP_PORTS):
        founder_secret = f"synthetic-audit-founder-secret-{party_id}-only"
        control_token = f"synthetic-audit-control-token-{party_id}-only"
        monkeypatch.setenv(f"MPC_NODE{party_id}_URL", f"http://127.0.0.1:{port}")
        monkeypatch.setenv(f"MPC_NODE{party_id}_TOKEN", control_token)
        monkeypatch.setenv(f"MPC_FOUNDER_TOKEN_SECRET_{party_id}", founder_secret)
        values[f"MPC_NODE{party_id}_URL"] = f"http://127.0.0.1:{port}"
        values[f"MPC_NODE{party_id}_TOKEN"] = control_token
        values[f"MPC_FOUNDER_TOKEN_SECRET_{party_id}"] = founder_secret
    for name, value in values.items():
        monkeypatch.setattr(settings, name, value)


async def _upgrade_and_verify_schema(database_url: str) -> None:
    """Apply the actual Alembic chain, then prove the expected tables exist."""
    # Alembic's async env calls asyncio.run(), so execute it in a worker thread
    # rather than nesting an event loop inside this async integration test.
    config = Config("alembic.ini")
    await asyncio.to_thread(command.upgrade, config, "head")
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            tables = set(
                (await connection.scalars(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                )).all()
            )
        assert revision == "0004_founder_display_name"
        assert {"benchmark_sessions", "accounts", "login_sessions"} <= tables
    finally:
        await engine.dispose()


async def _add_session(factory, session_id: str, state: str = SessionState.CREATED.value) -> None:
    now = datetime.now(timezone.utc)
    async with factory() as db:
        db.add(
            BenchmarkSession(
                id=session_id,
                state=state,
                created_at=now,
                expires_at=now + timedelta(minutes=30),
                submitted_party_ids=[0, 1, 2] if state == SessionState.READY.value else [],
            )
        )
        await db.commit()


class _BlockingStatusCoordinator:
    """Makes a real PostgreSQL advisory transaction lock observable."""

    def __init__(self) -> None:
        self.status_calls = 0
        self.first_status_started = asyncio.Event()
        self.release_first_status = asyncio.Event()

    async def get_statuses(self, _: str) -> list[dict[str, object]]:
        self.status_calls += 1
        if self.status_calls == 1:
            self.first_status_started.set()
            await self.release_first_status.wait()
        return []


class _BlockingComputeCoordinator:
    """Holds the first compute after its durable COMPUTING commit."""

    def __init__(self) -> None:
        self.execute_calls = 0
        self.first_compute_started = asyncio.Event()
        self.release_first_compute = asyncio.Event()

    async def execute_protocol(self, _: str, *, expires_at: int) -> dict[str, float | int]:
        del expires_at
        self.execute_calls += 1
        self.first_compute_started.set()
        await self.release_first_compute.wait()
        return {"aggregate_sum": 180_000, "average_salary": 60_000.0}

    async def shutdown_session(self, _: str, *, expires_at: int) -> None:
        del expires_at
        raise MPCExecutionFailed("not used by this test")


async def _assert_advisory_lock_and_compute_admission(database_url: str) -> None:
    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        await _add_session(factory, "refresh-lock")
        status_coordinator = _BlockingStatusCoordinator()
        async with factory() as first_db, factory() as second_db:
            first_record = await get_session(first_db, "refresh-lock")
            second_record = await get_session(second_db, "refresh-lock")
            first_refresh = asyncio.create_task(
                refresh_submission_state(first_db, first_record, status_coordinator)  # type: ignore[arg-type]
            )
            await asyncio.wait_for(status_coordinator.first_status_started.wait(), timeout=5)
            second_refresh = asyncio.create_task(
                refresh_submission_state(second_db, second_record, status_coordinator)  # type: ignore[arg-type]
            )
            await asyncio.sleep(0.25)
            # If pg_advisory_xact_lock were removed, both status calls would
            # have entered this blocking coordinator before the release.
            assert status_coordinator.status_calls == 1
            status_coordinator.release_first_status.set()
            await asyncio.gather(first_refresh, second_refresh)
        assert status_coordinator.status_calls == 2

        await _add_session(factory, "compute-one", SessionState.READY.value)
        await _add_session(factory, "compute-two", SessionState.READY.value)
        compute_coordinator = _BlockingComputeCoordinator()
        async with factory() as first_db, factory() as second_db:
            first_record = await get_session(first_db, "compute-one")
            second_record = await get_session(second_db, "compute-two")
            first_compute = asyncio.create_task(
                compute_session(first_db, first_record, compute_coordinator)  # type: ignore[arg-type]
            )
            await asyncio.wait_for(compute_coordinator.first_compute_started.wait(), timeout=5)
            with pytest.raises(SessionLifecycleError, match="Another computation is active"):
                await compute_session(second_db, second_record, compute_coordinator)  # type: ignore[arg-type]
            assert compute_coordinator.execute_calls == 1
            compute_coordinator.release_first_compute.set()
            completed = await first_compute
        assert completed.state == SessionState.COMPLETED.value
        assert compute_coordinator.execute_calls == 1
    finally:
        await engine.dispose()


async def _wait_for_party(port: int, process: asyncio.subprocess.Process) -> None:
    async with httpx.AsyncClient(timeout=2.0, trust_env=False) as client:
        for _ in range(90):
            if process.returncode is not None:
                raise AssertionError(f"Party {port} exited early ({process.returncode})")
            try:
                response = await client.get(f"http://127.0.0.1:{port}/health")
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.2)
    raise AssertionError(f"Party {port} did not start")


async def _assert_full_stack_three_party_round_trip(tmp_path: Path) -> None:
    """Use three separate HTTP party processes and real MPyC on loopback."""
    from backend.main import app
    from backend.services.database import database

    controls = [f"synthetic-audit-control-token-{party_id}-only" for party_id in range(3)]
    founder_secrets = [f"synthetic-audit-founder-secret-{party_id}-only" for party_id in range(3)]
    processes: list[asyncio.subprocess.Process] = []
    try:
        for party_id, port in enumerate(PARTY_HTTP_PORTS):
            child_environment = {
                **os.environ,
                "MPC_PARTY_ID": str(party_id),
                "MPC_PARTIES_COUNT": "3",
                "MPC_BASE_PORT": str(MPYC_PEER_PORT),
                "MPC_ENABLE_TLS": "false",
                "MPC_COORDINATOR_TOKEN": controls[party_id],
                "MPC_FOUNDER_TOKEN_SECRET": founder_secrets[party_id],
                "MPC_PARTY_STATE_DB_PATH": str(tmp_path / f"party-{party_id}.sqlite"),
                "MPC_PARTY_ALLOWED_ORIGINS": "http://127.0.0.1:3000",
                "ENVIRONMENT": "development",
                "NO_PROXY": "127.0.0.1,localhost",
                "no_proxy": "127.0.0.1,localhost",
            }
            for peer in range(3):
                child_environment[f"MPC_PARTY_{peer}_HOST"] = "127.0.0.1"
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "uvicorn",
                "backend.mpc.party_service:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--no-access-log",
                env=child_environment,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            processes.append(process)
        await asyncio.gather(*[_wait_for_party(port, process) for port, process in zip(PARTY_HTTP_PORTS, processes, strict=False)])

        await database.start()
        assert database.available, "Alembic-managed temporary PostgreSQL schema was not available"
        assert database.session_factory is not None
        async with database.session_factory() as db:
            db.add(Account(username="synthetic-admin", role="admin", password_hash=hash_password(ADMIN_PASSWORD)))
            await db.commit()

        async with (
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver", timeout=60.0) as coordinator,
            httpx.AsyncClient(timeout=30.0, trust_env=False) as party_client,
        ):
            login = await coordinator.post(
                "/api/v1/accounts/login",
                json={"username": "synthetic-admin", "password": ADMIN_PASSWORD},
            )
            assert login.status_code == 200, login.text
            admin_headers = {"Authorization": f"Bearer {login.json()['token']}"}
            created = await coordinator.post("/api/v1/sessions", headers=admin_headers, json={"ttl_minutes": 15})
            assert created.status_code == 201, created.text
            session_id = created.json()["session_id"]
            assert all(invite["capability_token"] == "" for invite in created.json()["founder_invites"])

            founder_tokens: list[str] = []
            for party_id, salary in enumerate(SYNTHETIC_SALARIES):
                username = f"synthetic-founder-{party_id}"
                invite = await coordinator.post(
                    "/api/v1/accounts/invitations",
                    headers=admin_headers,
                    json={"username": username, "session_id": session_id, "party_id": party_id},
                )
                assert invite.status_code == 201, invite.text
                activate = await coordinator.post(
                    "/api/v1/accounts/activate",
                    json={"username": username, "password": FOUNDER_PASSWORD, "invitation": invite.json()["invitation"]},
                )
                assert activate.status_code == 200, activate.text
                founder_login = await coordinator.post(
                    "/api/v1/accounts/login",
                    json={"username": username, "password": FOUNDER_PASSWORD},
                )
                assert founder_login.status_code == 200, founder_login.text
                founder_headers = {"Authorization": f"Bearer {founder_login.json()['token']}"}
                founder_tokens.append(founder_headers["Authorization"])
                assignment = await coordinator.get("/api/v1/accounts/assignment", headers=founder_headers)
                assert assignment.status_code == 200, assignment.text
                capability = assignment.json()
                assert capability["party_id"] == party_id
                submitted = await party_client.post(
                    f"http://127.0.0.1:{PARTY_HTTP_PORTS[party_id]}/sessions/{session_id}/input",
                    json={"salary": salary},
                    headers={"Authorization": f"Bearer {capability['capability']}"},
                )
                assert submitted.status_code == 200, submitted.text
                assert str(salary) not in submitted.text

            denied = await coordinator.get(
                f"/api/v1/sessions/{session_id}", headers={"Authorization": founder_tokens[0]}
            )
            assert denied.status_code == 403
            ready = await coordinator.get(f"/api/v1/sessions/{session_id}", headers=admin_headers)
            assert ready.status_code == 200, ready.text
            assert ready.json()["state"] == SessionState.READY.value
            assert ready.json()["submitted_party_ids"] == [0, 1, 2]
            computed = await coordinator.post(f"/api/v1/sessions/{session_id}/compute", headers=admin_headers)
            assert computed.status_code == 200, computed.text
            assert computed.json()["state"] == SessionState.COMPLETED.value
            assert computed.json()["result"] == {"aggregate_sum": 180_000, "average_salary": 60_000}
            assert "coordinator-compute;dur=" in computed.headers["Server-Timing"]
            assert '"private_input"' not in computed.text
            assert '"salary"' not in computed.text
            assert "50000" not in computed.text and "70000" not in computed.text
    finally:
        if database.available:
            await database.stop()
        for process in processes:
            if process.returncode is None:
                process.terminate()
        for process in processes:
            try:
                await asyncio.wait_for(process.wait(), timeout=8)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()


async def test_native_postgres_migrations_locks_and_three_party_mpyc(tmp_path, monkeypatch):
    """Verify migrations, PostgreSQL concurrency, and an actual 3-party flow."""
    database_url = _integration_database_url()
    _configure_test_runtime(monkeypatch, database_url)
    await _upgrade_and_verify_schema(database_url)
    await _assert_advisory_lock_and_compute_admission(database_url)
    await _assert_full_stack_three_party_round_trip(tmp_path)
