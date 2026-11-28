#!/usr/bin/env python3
"""Read-only public HTTPS smoke tests for the VEILBENCH academic deployment.

The script checks API/party health, CORS preflight, founder-route authentication,
and that private party-control routes are hidden from unauthenticated public
probes. It does not create sessions, submit salaries, or trigger MPC computation.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request(url: str, method: str = "GET", headers: dict[str, str] | None = None,
            body: bytes | None = None, timeout: float = 8.0) -> tuple[int, dict[str, str], bytes]:
    req = Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urlopen(req, timeout=timeout) as response:
            return response.status, dict(response.headers.items()), response.read()
    except HTTPError as error:
        return error.code, dict(error.headers.items()), error.read()


def retry_request(url: str, retries: int, delay: float) -> tuple[int, dict[str, str], bytes]:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            status, headers, body = request(url)
            if status == 200:
                return status, headers, body
            last_error = RuntimeError(f"HTTP {status}")
        except (URLError, TimeoutError, OSError) as error:
            last_error = error
        if attempt + 1 < retries:
            time.sleep(delay)
    raise RuntimeError(f"Endpoint did not become healthy: {url} ({last_error})")


def check_party(
    base_url: str, party_id: int, frontend_origin: str, *, require_mpyc_tls: bool
) -> None:
    base = base_url.rstrip("/")
    status, _, body = retry_request(f"{base}/health", retries=8, delay=2)
    data = json.loads(body)
    if status != 200 or data.get("status") != "healthy" or data.get("party_id") != party_id:
        raise RuntimeError(f"Party {party_id} health identity mismatch")
    if data.get("mpyc_tls_enabled") is not require_mpyc_tls:
        expected = "enabled" if require_mpyc_tls else "disabled for the co-hosted demo"
        raise RuntimeError(f"Party {party_id} MPyC TLS flag did not match the expected {expected} mode")
    tls_mode = "enabled" if require_mpyc_tls else "disabled in the explicitly co-hosted demo mode"
    print(f"PASS: Party {party_id} public health; MPyC TLS is {tls_mode}")

    session_id = str(uuid.uuid4())
    preflight_status, preflight_headers, _ = request(
        f"{base}/sessions/{session_id}/input",
        method="OPTIONS",
        headers={
            "Origin": frontend_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    allowed_origin = next((value for key, value in preflight_headers.items()
                           if key.lower() == "access-control-allow-origin"), None)
    if preflight_status not in (200, 204) or allowed_origin != frontend_origin:
        raise RuntimeError(f"Party {party_id} CORS preflight failed (HTTP {preflight_status})")
    print(f"PASS: Party {party_id} CORS allows the configured Vercel origin")

    input_status, _, input_body = request(
        f"{base}/sessions/{session_id}/input",
        method="POST",
        headers={"Content-Type": "application/json", "Origin": frontend_origin},
        body=b'{"salary":50000}',
    )
    if input_status != 401:
        raise RuntimeError(
            f"Party {party_id} founder input route should reject a missing capability with HTTP 401; got {input_status}"
        )
    if b"50000" in input_body:
        raise RuntimeError(f"Party {party_id} echoed a submitted salary in an error response")
    print(f"PASS: Party {party_id} founder endpoint is reachable but rejects missing capability")

    control_status, _, _ = request(f"{base}/sessions/{session_id}/status")
    if control_status != 404:
        raise RuntimeError(f"Party {party_id} control/status route is publicly reachable (HTTP {control_status})")
    compute_status, _, _ = request(
        f"{base}/sessions/{session_id}/compute", method="POST", body=b"{}",
        headers={"Content-Type": "application/json"},
    )
    if compute_status != 404:
        raise RuntimeError(f"Party {party_id} compute route is publicly reachable (HTTP {compute_status})")
    print(f"PASS: Party {party_id} control and compute routes are hidden by the public proxy")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--party-0-url", required=True)
    parser.add_argument("--party-1-url", required=True)
    parser.add_argument("--party-2-url", required=True)
    parser.add_argument("--frontend-origin", required=True)
    parser.add_argument(
        "--allow-cohosted-mpc",
        action="store_true",
        help="Verify the $0 single-container demo where MPyC peer TLS is intentionally disabled.",
    )
    parser.add_argument("--retries", type=int, default=6)
    parser.add_argument("--retry-delay", type=float, default=3.0)
    args = parser.parse_args()
    if args.retries < 1 or args.retry_delay < 0:
        parser.error("--retries must be positive and --retry-delay non-negative")

    try:
        api = args.api_url.rstrip("/")
        status, _, body = retry_request(f"{api}/health/ready", args.retries, args.retry_delay)
        data = json.loads(body)
        if status != 200 or data.get("status") != "ready":
            raise RuntimeError("Coordinator readiness response is invalid")
        print("PASS: Coordinator API and PostgreSQL readiness")
        for party_id, url in enumerate((args.party_0_url, args.party_1_url, args.party_2_url)):
            check_party(
                url,
                party_id,
                args.frontend_origin.rstrip("/"),
                require_mpyc_tls=not args.allow_cohosted_mpc,
            )
    except (RuntimeError, ValueError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("\nAll public deployment smoke checks passed. No salary was submitted and no MPC job was started.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
