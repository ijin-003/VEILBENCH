"""Run an explicit, synthetic three-founder MPC smoke test against public HTTPS URLs.

This script creates one short-lived session, submits fixed demonstration salaries
straight to the three public party endpoints, waits for READY, triggers MPC via
the coordinator, and verifies only the aggregate result. It never prints the
admin token, founder capabilities, or individual salary values.

Run from the project root on the VPS host:
    python3 -m backend.ops.smoke_test_mpc_e2e \
        --env-file .env.production --confirm-synthetic-data
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

DEMO_SALARIES = (50_000, 70_000, 60_000)
EXPECTED_SUM = sum(DEMO_SALARIES)
EXPECTED_AVERAGE = EXPECTED_SUM / len(DEMO_SALARIES)
PRIVATE_FIELD_NAMES = {"salary", "salaries", "private_input", "private_inputs", "share", "shares"}


def load_env_file(path: Path) -> dict[str, str]:
    """Read the simple KEY=VALUE format written by generate_production_env.py."""
    if not path.is_file():
        raise RuntimeError(f"Environment file does not exist: {path}")
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise RuntimeError(f"Invalid environment entry at line {line_number}")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in values:
            raise RuntimeError(f"Empty or duplicate environment key at line {line_number}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def _contains_private_field(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).lower() in PRIVATE_FIELD_NAMES or _contains_private_field(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_private_field(child) for child in value)
    return False


def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> tuple[int, dict[str, str], dict[str, Any]]:
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    request_headers = dict(headers or {})
    if body is not None:
        request_headers.setdefault("Content-Type", "application/json")
    request = Request(url, data=payload, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status_code = response.status
            response_headers = dict(response.headers.items())
    except HTTPError as error:
        raw = error.read()
        status_code = error.code
        response_headers = dict(error.headers.items())
    except (URLError, TimeoutError, OSError) as error:
        raise RuntimeError("A public VEILBENCH endpoint could not be reached") from error
    try:
        parsed = json.loads(raw.decode("utf-8")) if raw else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("A public VEILBENCH endpoint returned invalid JSON") from error
    if not isinstance(parsed, dict):
        raise RuntimeError("A public VEILBENCH endpoint returned an unexpected response")
    return status_code, response_headers, parsed


def _require_https_origin(name: str, value: str) -> str:
    parsed = urlsplit(value.rstrip("/"))
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError(f"{name} must be a public HTTPS origin")
    return value.rstrip("/")


def run_e2e(
    values: dict[str, str],
    *,
    confirmed: bool,
    request_fn: Callable[..., tuple[int, dict[str, str], dict[str, Any]]] = request_json,
    timeout_seconds: float = 120.0,
    poll_interval_seconds: float = 2.0,
    sleep_fn: Callable[[float], None] = time.sleep,
    monotonic_fn: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Exercise the complete public founder-to-MPyC workflow with synthetic data."""
    if not confirmed:
        raise RuntimeError("Pass --confirm-synthetic-data to authorize three synthetic submissions")
    admin_token = values.get("COORDINATOR_ADMIN_TOKEN", "")
    if len(admin_token) < 32:
        raise RuntimeError("COORDINATOR_ADMIN_TOKEN is missing or too short in the environment file")

    api_url = _require_https_origin("NEXT_PUBLIC_API_URL", values.get("NEXT_PUBLIC_API_URL", ""))
    frontend_origin = _require_https_origin("FRONTEND_PUBLIC_URL", values.get("FRONTEND_PUBLIC_URL", ""))
    party_urls = [
        _require_https_origin(
            f"NEXT_PUBLIC_PARTY_{party_id}_URL",
            values.get(f"NEXT_PUBLIC_PARTY_{party_id}_URL", ""),
        )
        for party_id in range(3)
    ]
    if len(set(party_urls)) != 3:
        raise RuntimeError("The three public party URLs must be distinct")

    admin_headers = {
        "X-VEILBENCH-Admin-Token": admin_token,
        "Origin": frontend_origin,
    }
    status_code, response_headers, created = request_fn(
        f"{api_url}/api/v1/sessions",
        method="POST",
        headers=admin_headers,
        body={"ttl_minutes": 5},
    )
    if status_code != 201:
        raise RuntimeError(f"Coordinator did not create a test session (HTTP {status_code})")
    cache_control = next(
        (value for key, value in response_headers.items() if key.lower() == "cache-control"), ""
    ).lower()
    if "no-store" not in cache_control:
        raise RuntimeError("Founder invitation response is missing Cache-Control: no-store")
    if _contains_private_field(created):
        raise RuntimeError("Coordinator session-creation response contains a private-input field")

    session_id = created.get("session_id")
    invites = created.get("founder_invites")
    if not isinstance(session_id, str) or not isinstance(invites, list) or len(invites) != 3:
        raise RuntimeError("Coordinator did not return one invitation for each founder")
    invite_by_party: dict[int, dict[str, Any]] = {}
    for invite in invites:
        if not isinstance(invite, dict):
            raise RuntimeError("Coordinator returned an invalid founder invitation")
        party_id = invite.get("party_id")
        if party_id not in range(3) or party_id in invite_by_party:
            raise RuntimeError("Founder invitations do not map uniquely to the three parties")
        invite_by_party[party_id] = invite
    if set(invite_by_party) != {0, 1, 2}:
        raise RuntimeError("A founder invitation is missing")

    for party_id, salary in enumerate(DEMO_SALARIES):
        invite = invite_by_party[party_id]
        capability = invite.get("capability_token")
        submission_api = invite.get("submission_api")
        if not isinstance(capability, str) or not capability:
            raise RuntimeError(f"Founder {party_id + 1} invitation has no capability")
        expected_api = f"{party_urls[party_id]}/sessions/{session_id}/input"
        expected_page = f"{frontend_origin}/submit/{session_id}/{party_id}"
        if submission_api != expected_api:
            raise RuntimeError(f"Founder {party_id + 1} invitation targets the wrong party URL")
        if invite.get("submission_page") != expected_page:
            raise RuntimeError(f"Founder {party_id + 1} invitation targets the wrong frontend page")
        status_code, _, accepted = request_fn(
            submission_api,
            method="POST",
            headers={
                "Authorization": f"Bearer {capability}",
                "Origin": frontend_origin,
            },
            body={"salary": salary},
        )
        if status_code != 200 or accepted.get("party_id") != party_id or accepted.get("input_submitted") is not True:
            raise RuntimeError(f"Assigned party {party_id} did not confirm its founder submission")
        if _contains_private_field(accepted):
            raise RuntimeError(f"Party {party_id} response exposed a private-input field")

    deadline = monotonic_fn() + timeout_seconds
    while True:
        status_code, _, session = request_fn(
            f"{api_url}/api/v1/sessions/{session_id}",
            headers=admin_headers,
        )
        if status_code != 200:
            raise RuntimeError(f"Coordinator status check failed (HTTP {status_code})")
        if _contains_private_field(session):
            raise RuntimeError("Coordinator status response contains a private-input field")
        state = str(session.get("state", "")).lower()
        if state == "ready" and sorted(session.get("submitted_party_ids", [])) == [0, 1, 2]:
            break
        if state in {"failed", "expired"}:
            raise RuntimeError(f"Test session entered terminal state: {state}")
        if monotonic_fn() >= deadline:
            raise RuntimeError("All three founder submissions were not confirmed before timeout")
        sleep_fn(poll_interval_seconds)

    status_code, _, completed = request_fn(
        f"{api_url}/api/v1/sessions/{session_id}/compute",
        method="POST",
        headers=admin_headers,
    )
    if status_code != 200 or str(completed.get("state", "")).lower() != "completed":
        raise RuntimeError(f"Coordinator did not complete the MPC computation (HTTP {status_code})")
    if _contains_private_field(completed):
        raise RuntimeError("Coordinator computation response contains a private-input field")
    result = completed.get("result")
    if not isinstance(result, dict) or set(result) != {"aggregate_sum", "average_salary"}:
        raise RuntimeError("Coordinator did not return exactly the permitted aggregate result fields")
    try:
        aggregate_sum = int(result["aggregate_sum"])
        average_salary = float(result["average_salary"])
    except (TypeError, ValueError) as error:
        raise RuntimeError("Coordinator returned invalid aggregate result types") from error
    if aggregate_sum != EXPECTED_SUM or not math.isclose(average_salary, EXPECTED_AVERAGE, rel_tol=0, abs_tol=1e-9):
        raise RuntimeError("The three-party MPC result did not match the synthetic demonstration aggregate")

    return {
        "session_id": session_id,
        "state": "completed",
        "aggregate_sum": aggregate_sum,
        "average_salary": average_salary,
        "founders_confirmed": 3,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=".env.production", help="Private production env file")
    parser.add_argument(
        "--confirm-synthetic-data",
        action="store_true",
        help="Explicitly authorize one synthetic three-founder test computation",
    )
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--poll-interval-seconds", type=float, default=2.0)
    args = parser.parse_args()
    if args.timeout_seconds <= 0 or args.poll_interval_seconds <= 0:
        parser.error("Timeout and polling interval must be positive")
    try:
        values = load_env_file(Path(args.env_file))
        result = run_e2e(
            values,
            confirmed=args.confirm_synthetic_data,
            timeout_seconds=args.timeout_seconds,
            poll_interval_seconds=args.poll_interval_seconds,
        )
    except (OSError, RuntimeError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: three founder submissions reached their assigned public MPC parties")
    print("PASS: coordinator returned no private-input fields")
    print("PASS: all three parties completed the MPyC computation")
    print(f"PASS: aggregate sum = {result['aggregate_sum']}")
    print(f"PASS: average salary = {result['average_salary']:.2f}")
    print(f"Session: {result['session_id']}")
    print("The test used synthetic demonstration values only; no individual values or capabilities were printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
