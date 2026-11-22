"""Phase C timing regression: server-side duration without private information."""
import importlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Response

from backend.models.session import BenchmarkSession


@pytest.mark.asyncio
async def test_compute_response_exposes_safe_duration_only(monkeypatch):
    api = importlib.import_module("backend.api.sessions")
    now = datetime.now(timezone.utc)
    record = BenchmarkSession(
        id="synthetic-metrics",
        state="ready",
        created_at=now,
        expires_at=now + timedelta(minutes=15),
        submitted_party_ids=[0, 1, 2],
    )
    result = BenchmarkSession(
        id="synthetic-metrics",
        state="completed",
        created_at=now,
        expires_at=now + timedelta(minutes=15),
        submitted_party_ids=[0, 1, 2],
        aggregate_sum=180000,
        average_salary=60000,
    )
    calls = []

    async def fake_get(db, session_id):
        calls.append("load")
        assert session_id == "synthetic-metrics"
        return record

    async def fake_refresh(db, current, coordinator):
        calls.append("refresh")
        return current

    async def fake_compute(db, current, coordinator):
        calls.append("compute")
        return result

    monkeypatch.setattr(api, "get_session", fake_get)
    monkeypatch.setattr(api, "refresh_submission_state", fake_refresh)
    monkeypatch.setattr(api, "compute_session", fake_compute)
    monkeypatch.setattr(api, "_coordinator", lambda: object())
    response = Response()
    view = await api.run_session("synthetic-metrics", None, object(), response)
    assert calls == ["load", "refresh", "compute"]
    assert view.result.aggregate_sum == 180000
    assert response.headers["Cache-Control"] == "no-store"
    metric = response.headers["Server-Timing"]
    assert metric.startswith("coordinator-compute;dur=")
    assert float(metric.split("=", 1)[1]) >= 0
    assert "synthetic" not in metric
    assert "50000" not in metric


@pytest.mark.asyncio
async def test_failed_compute_does_not_claim_successful_timing(monkeypatch):
    api = importlib.import_module("backend.api.sessions")
    async def fail_get(db, session_id):
        raise LookupError("unknown")
    monkeypatch.setattr(api, "get_session", fail_get)
    response = Response()
    with pytest.raises(Exception) as caught:
        await api.run_session("unknown", None, object(), response)
    assert getattr(caught.value, "status_code", None) == 404
    assert "Server-Timing" not in response.headers
    assert response.headers["Cache-Control"] == "no-store"
