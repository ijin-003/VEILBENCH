from backend.main import app


def test_coordinator_openapi_has_no_salary_submission_route():
    paths = app.openapi()["paths"]
    assert "/api/v1/sessions/{session_id}/input" not in paths
    assert "/api/v1/sessions" in paths
