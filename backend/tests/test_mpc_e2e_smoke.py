from pathlib import Path

import pytest

from backend.ops.smoke_test_mpc_e2e import (
    DEMO_SALARIES,
    run_e2e,
)


BASE_VALUES = {
    "COORDINATOR_ADMIN_TOKEN": "a" * 48,
    "NEXT_PUBLIC_API_URL": "https://api.demo.test",
    "NEXT_PUBLIC_PARTY_0_URL": "https://party0.demo.test",
    "NEXT_PUBLIC_PARTY_1_URL": "https://party1.demo.test",
    "NEXT_PUBLIC_PARTY_2_URL": "https://party2.demo.test",
    "FRONTEND_PUBLIC_URL": "https://demo.vercel.app",
}


def _fake_request_factory(*, aggregate_sum=180_000, average_salary=60_000.0):
    calls = []
    session_id = "12345678-1234-4234-8234-123456789abc"
    invites = [
        {
            "party_id": party_id,
            "submission_page": f"https://demo.vercel.app/submit/{session_id}/{party_id}",
            "submission_api": f"https://party{party_id}.demo.test/sessions/{session_id}/input",
            "capability_token": f"capability-{party_id}",
        }
        for party_id in range(3)
    ]

    def fake_request(url, *, method="GET", headers=None, body=None, timeout=10.0):
        calls.append((url, method, headers or {}, body))
        if url == "https://api.demo.test/api/v1/sessions" and method == "POST":
            return 201, {"Cache-Control": "no-store, no-cache"}, {
                "session_id": session_id,
                "state": "created",
                "founder_invites": invites,
            }
        if "/input" in url and method == "POST":
            party_id = int(url.split("party", 1)[1].split(".", 1)[0])
            assert body == {"salary": DEMO_SALARIES[party_id]}
            assert headers["Authorization"] == f"Bearer capability-{party_id}"
            return 200, {}, {"status": "accepted", "party_id": party_id, "input_submitted": True}
        if url == f"https://api.demo.test/api/v1/sessions/{session_id}" and method == "GET":
            return 200, {}, {"session_id": session_id, "state": "ready", "submitted_party_ids": [0, 1, 2]}
        if url == f"https://api.demo.test/api/v1/sessions/{session_id}/compute" and method == "POST":
            return 200, {}, {
                "session_id": session_id,
                "state": "completed",
                "result": {"aggregate_sum": aggregate_sum, "average_salary": average_salary},
            }
        raise AssertionError(f"Unexpected smoke-test request: {method} {url}")

    return fake_request, calls


def test_e2e_smoke_submits_directly_to_three_parties_and_checks_aggregate():
    fake_request, calls = _fake_request_factory()
    result = run_e2e(
        BASE_VALUES,
        confirmed=True,
        request_fn=fake_request,
        sleep_fn=lambda _seconds: None,
        monotonic_fn=lambda: 0.0,
    )

    assert result["state"] == "completed"
    assert result["founders_confirmed"] == 3
    assert result["aggregate_sum"] == 180_000
    assert result["average_salary"] == 60_000.0
    founder_calls = [call for call in calls if "/input" in call[0]]
    assert len(founder_calls) == 3
    assert all("api.demo.test" not in call[0] for call in founder_calls)
    coordinator_calls = [call for call in calls if "api.demo.test" in call[0]]
    assert all(call[3] is None or "salary" not in call[3] for call in coordinator_calls)


def test_e2e_smoke_requires_explicit_synthetic_data_confirmation():
    fake_request, _ = _fake_request_factory()
    with pytest.raises(RuntimeError, match="confirm-synthetic-data"):
        run_e2e(BASE_VALUES, confirmed=False, request_fn=fake_request)


def test_e2e_smoke_rejects_mismatched_party_invitation():
    fake_request, _ = _fake_request_factory()

    def wrong_invite(url, **kwargs):
        status, headers, payload = fake_request(url, **kwargs)
        if url == "https://api.demo.test/api/v1/sessions" and kwargs.get("method") == "POST":
            payload["founder_invites"][0]["submission_api"] = (
                "https://party1.demo.test/sessions/12345678-1234-4234-8234-123456789abc/input"
            )
        return status, headers, payload

    with pytest.raises(RuntimeError, match="wrong party URL"):
        run_e2e(
            BASE_VALUES,
            confirmed=True,
            request_fn=wrong_invite,
            sleep_fn=lambda _seconds: None,
            monotonic_fn=lambda: 0.0,
        )


def test_e2e_smoke_rejects_incorrect_mpc_aggregate():
    fake_request, _ = _fake_request_factory(aggregate_sum=180_001, average_salary=60_000.333)
    with pytest.raises(RuntimeError, match="did not match"):
        run_e2e(
            BASE_VALUES,
            confirmed=True,
            request_fn=fake_request,
            sleep_fn=lambda _seconds: None,
            monotonic_fn=lambda: 0.0,
        )


def test_e2e_smoke_rejects_private_fields_in_coordinator_response():
    fake_request, _ = _fake_request_factory()

    def leaking_request(url, **kwargs):
        status, headers, payload = fake_request(url, **kwargs)
        if url == "https://api.demo.test/api/v1/sessions" and kwargs.get("method") == "POST":
            payload["salary"] = 50_000
        return status, headers, payload

    with pytest.raises(RuntimeError, match="private-input field"):
        run_e2e(
            BASE_VALUES,
            confirmed=True,
            request_fn=leaking_request,
            sleep_fn=lambda _seconds: None,
            monotonic_fn=lambda: 0.0,
        )


def test_deploy_builds_images_sequentially_before_starting_services():
    root = Path(__file__).resolve().parents[2]
    deploy = (root / "scripts/deploy_vps.sh").read_text(encoding="utf-8")
    builder = (root / "scripts/build_production_images.sh").read_text(encoding="utf-8")
    assert "scripts/build_production_images.sh" in deploy
    assert 'up -d --no-build --remove-orphans' in deploy
    assert 'up -d --build' not in deploy
    assert 'for service in veilbench-backend veilbench-mpc-node0 veilbench-mpc-node1 veilbench-mpc-node2' in builder
    assert 'build --pull "$service"' in builder
    assert 'pull veilbench-db veilbench-edge' in builder
