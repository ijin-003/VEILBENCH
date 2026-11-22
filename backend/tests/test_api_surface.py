from backend.main import app


def test_coordinator_openapi_has_no_salary_submission_route():
    paths = app.openapi()["paths"]
    assert "/api/v1/sessions/{session_id}/input" not in paths
    assert "/api/v1/sessions" in paths


def test_admin_recovery_route_is_available():
    paths = app.openapi()["paths"]
    assert "/api/v1/sessions/{session_id}/recover" in paths
    assert "post" in paths["/api/v1/sessions/{session_id}/recover"]


def test_coordinator_contract_never_accepts_plaintext_salary():
    schema = app.openapi()
    paths = schema["paths"]
    assert not any(path.endswith("/input") for path in paths)
    for path_item in paths.values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            request_body = operation.get("requestBody", {})
            content = request_body.get("content", {})
            for media in content.values():
                schema_ref = media.get("schema", {})
                assert "salary" not in str(schema_ref).lower()


def test_founder_invite_response_is_marked_no_store():
    import asyncio
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from fastapi import Response

    from backend.api import sessions as sessions_api

    now = datetime.now(timezone.utc)
    record = SimpleNamespace(
        id="session-test",
        state="created",
        created_at=now,
        expires_at=now + timedelta(minutes=30),
        submitted_party_ids=[],
        aggregate_sum=None,
        average_salary=None,
        failure_reason=None,
    )

    async def run():
        response = Response()
        with patch.object(sessions_api, "_coordinator", return_value=object()), patch.object(
            sessions_api, "create_session", new=AsyncMock(return_value=record)
        ), patch.object(
            sessions_api.settings,
            "FRONTEND_PUBLIC_URL",
            "https://demo.example.test",
        ), patch.object(
            sessions_api.settings,
            "MPC_PARTY_PUBLIC_URLS",
            [
                "https://party0.example.test",
                "https://party1.example.test",
                "https://party2.example.test",
            ],
        ), patch.object(
            sessions_api.settings, "MPC_FOUNDER_TOKEN_SECRET_0", "founder-secret-0"
        ), patch.object(
            sessions_api.settings, "MPC_FOUNDER_TOKEN_SECRET_1", "founder-secret-1"
        ), patch.object(
            sessions_api.settings, "MPC_FOUNDER_TOKEN_SECRET_2", "founder-secret-2"
        ):
            created = await sessions_api.start_session(
                sessions_api.CreateSessionRequest(ttl_minutes=30), response, None, object()
            )

        assert [invite.party_id for invite in created.founder_invites] == [0, 1, 2]
        assert len({invite.capability_token for invite in created.founder_invites}) == 3
        assert [invite.submission_api for invite in created.founder_invites] == [
            "https://party0.example.test/sessions/session-test/input",
            "https://party1.example.test/sessions/session-test/input",
            "https://party2.example.test/sessions/session-test/input",
        ]
        assert all("capability" not in invite.submission_page for invite in created.founder_invites)
        assert response.headers["cache-control"].startswith("no-store")
        assert response.headers["pragma"] == "no-cache"

    asyncio.run(run())


def test_readiness_and_liveness_routes_are_registered():
    paths = app.openapi()["paths"]
    assert "/health/live" in paths
    assert "/health/ready" in paths
    assert "/api/v1/health/live" in paths
    assert "/api/v1/health/ready" in paths
