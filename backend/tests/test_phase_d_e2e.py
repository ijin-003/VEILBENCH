"""Phase D: authenticated full-stack acceptance with disposable services.

Runs the actual coordinator API, PostgreSQL, three HTTP party services and
the three MPyC worker subprocesses. No production credentials, users, domains,
or databases are accessed. Opt-in via VEILBENCH_E2E_LOCAL=1.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sys
import time

import httpx
import pytest

pytestmark = pytest.mark.asyncio

PARTY_HTTP_PORTS = (18130, 18131, 18132)
MPYC_PEER_PORT = 19130
SYNTHETIC_SALARIES = (50000, 70000, 60000)
TEST_PASSWORD = "synthetic-founder-password-only"
ADMIN_PASSWORD = "synthetic-admin-password-only"


async def _wait_for_party(port: int, process: asyncio.subprocess.Process) -> None:
    async with httpx.AsyncClient(timeout=2.0, trust_env=False) as client:
        for _ in range(90):
            if process.returncode is not None:
                raise AssertionError(f"Local party on {port} exited early ({process.returncode})")
            try:
                response = await client.get(f"http://127.0.0.1:{port}/health")
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.2)
    raise AssertionError(f"Local party on {port} did not start")


@pytest.mark.skipif(os.environ.get("VEILBENCH_E2E_LOCAL") != "1", reason="requires disposable PostgreSQL and local party processes")
async def test_admin_founders_real_mpyc_database_round_trip(tmp_path, monkeypatch):
    # Guard against accidentally directing any request to a hosted service.
    db_url = os.environ.get("VEILBENCH_E2E_DATABASE_URL", "")
    assert db_url.startswith("postgresql+asyncpg://")
    assert "@127.0.0.1:" in db_url or "@localhost:" in db_url
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DATABASE_AUTO_CREATE", "true")
    monkeypatch.setenv("MPC_REQUIRE_TLS", "false")
    monkeypatch.setenv("FRONTEND_PUBLIC_URL", "http://127.0.0.1:3000")
    monkeypatch.setenv("MPC_PARTIES_COUNT", "3")
    monkeypatch.setenv("MPC_THRESHOLD", "1")
    monkeypatch.setenv("SESSION_TTL_SECONDS", "1800")
    monkeypatch.setenv("COORDINATOR_ADMIN_TOKEN", "synthetic-local-admin-control-credential")
    monkeypatch.setenv("MPC_PARTY_PUBLIC_URLS", json.dumps([
        f"http://127.0.0.1:{port}" for port in PARTY_HTTP_PORTS
    ]))
    secrets_by_party = [
        f"synthetic-party-{index}-founder-signing-secret-only" for index in range(3)
    ]
    controls = [f"synthetic-party-{index}-coordinator-control-only" for index in range(3)]
    for index, port in enumerate(PARTY_HTTP_PORTS):
        monkeypatch.setenv(f"MPC_NODE{index}_URL", f"http://127.0.0.1:{port}")
        monkeypatch.setenv(f"MPC_NODE{index}_TOKEN", controls[index])
        monkeypatch.setenv(f"MPC_FOUNDER_TOKEN_SECRET_{index}", secrets_by_party[index])

    # Import only after configuring settings: pydantic Settings is initialized
    # once when the backend is imported.
    from backend.main import app
    from backend.models.account import Account
    from backend.security.accounts import hash_password
    from backend.services.database import database

    processes: list[asyncio.subprocess.Process] = []
    try:
        for index, port in enumerate(PARTY_HTTP_PORTS):
            env = {
                **os.environ,
                "MPC_PARTY_ID": str(index),
                "MPC_PARTIES_COUNT": "3",
                "MPC_BASE_PORT": str(MPYC_PEER_PORT),
                "MPC_ENABLE_TLS": "false",
                "MPC_COORDINATOR_TOKEN": controls[index],
                "MPC_FOUNDER_TOKEN_SECRET": secrets_by_party[index],
                "MPC_PARTY_STATE_DB_PATH": str(tmp_path / f"party-{index}.sqlite"),
                "MPC_PARTY_ALLOWED_ORIGINS": "http://127.0.0.1:3000",
                "ENVIRONMENT": "development",
                "NO_PROXY": "127.0.0.1,localhost",
                "no_proxy": "127.0.0.1,localhost",
            }
            for peer in range(3):
                env[f"MPC_PARTY_{peer}_HOST"] = "127.0.0.1"
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "uvicorn", "backend.mpc.party_service:app",
                "--host", "127.0.0.1", "--port", str(port), "--no-access-log",
                env=env,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            processes.append(process)

        await asyncio.gather(*[
            _wait_for_party(port, process)
            for port, process in zip(PARTY_HTTP_PORTS, processes)
        ])
        await database.start()
        assert database.available, "Temporary PostgreSQL was not initialized"
        async with database.session_factory() as db:
            db.add(Account(
                username="syntheticadmin",
                role="admin",
                password_hash=hash_password(ADMIN_PASSWORD),
            ))
            await db.commit()

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
            timeout=60.0,
        ) as coordinator, httpx.AsyncClient(
            timeout=30.0, trust_env=False
        ) as party_client:
            login = await coordinator.post("/api/v1/accounts/login", json={
                "username": "syntheticadmin", "password": ADMIN_PASSWORD,
            })
            assert login.status_code == 200, (login.status_code, login.text)
            admin_token = login.json()["token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            created = await coordinator.post(
                "/api/v1/sessions", headers=admin_headers,
                json={"ttl_minutes": 15},
            )
            assert created.status_code == 201, (created.status_code, created.text)
            session = created.json()
            session_id = session["session_id"]
            assert session["state"] == "created"
            assert len(session["founder_invites"]) == 3
            assert all(item["capability_token"] == "" for item in session["founder_invites"])
            print("CHECK session creation: PASS (no coordinator salary input)", flush=True)

            founder_logins = []
            for party_id in range(3):
                username = f"syntheticfounder{party_id}"
                invitation_response = await coordinator.post(
                    "/api/v1/accounts/invitations",
                    headers=admin_headers,
                    json={"username": username, "session_id": session_id, "party_id": party_id},
                )
                assert invitation_response.status_code == 201
                invitation = invitation_response.json()["invitation"]

                activation = await coordinator.post("/api/v1/accounts/activate", json={
                    "username": username,
                    "password": TEST_PASSWORD,
                    "invitation": invitation,
                })
                assert activation.status_code == 200
                replay = await coordinator.post("/api/v1/accounts/activate", json={
                    "username": username,
                    "password": TEST_PASSWORD,
                    "invitation": invitation,
                })
                assert replay.status_code == 400

                founder_login = await coordinator.post("/api/v1/accounts/login", json={
                    "username": username, "password": TEST_PASSWORD,
                })
                assert founder_login.status_code == 200
                token = founder_login.json()["token"]
                founder_logins.append(token)
                founder_headers = {"Authorization": f"Bearer {token}"}
                assignment = await coordinator.get(
                    "/api/v1/accounts/assignment", headers=founder_headers
                )
                assert assignment.status_code == 200
                capability = assignment.json()
                assert capability["party_id"] == party_id
                assert capability["session_id"] == session_id

                # A real HTTP request to the assigned party, NOT the coordinator.
                endpoint = f"http://127.0.0.1:{PARTY_HTTP_PORTS[party_id]}/sessions/{session_id}/input"
                submitted = await party_client.post(
                    endpoint,
                    json={"salary": SYNTHETIC_SALARIES[party_id]},
                    headers={"Authorization": f"Bearer {capability['capability']}"},
                )
                assert submitted.status_code == 200, submitted.status_code
                assert "salary" not in submitted.json()

                duplicate = await party_client.post(
                    endpoint,
                    json={"salary": 99999},
                    headers={"Authorization": f"Bearer {capability['capability']}"},
                )
                assert duplicate.status_code == 409
                assert "99999" not in duplicate.text
                print(f"CHECK founder {party_id}: activated, privately submitted, replay rejected", flush=True)

            # A founder cannot act as the administrator.
            denied = await coordinator.get(
                f"/api/v1/sessions/{session_id}",
                headers={"Authorization": f"Bearer {founder_logins[0]}"},
            )
            assert denied.status_code == 403

            ready = await coordinator.get(
                f"/api/v1/sessions/{session_id}", headers=admin_headers
            )
            assert ready.status_code == 200
            assert ready.json()["state"] == "ready"
            assert ready.json()["submitted_party_ids"] == [0, 1, 2]
            print("CHECK all three registered, only metadata visible: PASS", flush=True)

            compute = await coordinator.post(
                f"/api/v1/sessions/{session_id}/compute", headers=admin_headers
            )
            assert compute.status_code == 200, (compute.status_code, compute.text)
            computed = compute.json()
            assert computed["state"] == "completed"
            assert computed["result"] == {
                "aggregate_sum": 180000, "average_salary": 60000.0
            }
            assert "coordinator-compute;dur=" in compute.headers["Server-Timing"]
            print("CHECK real 3-party MPyC aggregate 180000, average 60000: PASS", flush=True)

            # Confirm the result survived DB transaction boundaries and can be
            # re-read without re-running MPyC or leaking individual salaries.
            refreshed = await coordinator.get(
                f"/api/v1/sessions/{session_id}", headers=admin_headers
            )
            assert refreshed.status_code == 200
            assert refreshed.json()["state"] == "completed"
            assert refreshed.json()["result"] == computed["result"]
            assert "private_input" not in refreshed.text.lower()\n            assert "founder_salary" not in refreshed.text.lower()
            assert "50000" not in refreshed.text and "70000" not in refreshed.text
            print("CHECK persisted aggregate after fresh status fetch: PASS", flush=True)
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
