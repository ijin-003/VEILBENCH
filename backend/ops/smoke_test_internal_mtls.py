"""Verify internal mTLS and reject unauthenticated TLS clients to MPC parties.

Run inside the backend container after deployment. It confirms that the
coordinator client certificate is accepted by each party and that a TLS
client without a certificate cannot complete the handshake.
"""
from __future__ import annotations

import json
import ssl
import sys
from http.client import RemoteDisconnected
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

from backend.config import settings


def _context(*, with_client_certificate: bool) -> ssl.SSLContext:
    if not settings.MPC_CA_CERT_PATH or not Path(settings.MPC_CA_CERT_PATH).is_file():
        raise RuntimeError("Internal mTLS CA certificate is not configured")
    context = ssl.create_default_context(cafile=settings.MPC_CA_CERT_PATH)
    if with_client_certificate:
        if not settings.MPC_CLIENT_CERT_PATH or not settings.MPC_CLIENT_KEY_PATH:
            raise RuntimeError("Coordinator client certificate is not configured")
        context.load_cert_chain(settings.MPC_CLIENT_CERT_PATH, settings.MPC_CLIENT_KEY_PATH)
    return context


def _assert_anonymous_rejected(url: str, anonymous: ssl.SSLContext, service: str) -> None:
    try:
        with urlopen(url, context=anonymous, timeout=5) as response:
            raise RuntimeError(
                f"{service} accepted a TLS client without a certificate (HTTP {response.status})"
            )
    except (ssl.SSLError, ConnectionResetError, RemoteDisconnected):
        pass
    except HTTPError as error:
        # Receiving an HTTP response means the TLS handshake completed, so an
        # application-level denial is not proof that mTLS is required.
        raise RuntimeError(
            f"{service} completed anonymous TLS and returned HTTP {error.code}"
        ) from error
    except URLError as error:
        # Uvicorn/OpenSSL may report a required-client-certificate alert as an
        # SSL error or a peer close before HTTP starts, depending on TLS version.
        if not isinstance(error.reason, (ssl.SSLError, ConnectionResetError, RemoteDisconnected)):
            raise RuntimeError(f"{service} anonymous TLS probe failed unexpectedly") from error


def _check_backend(authenticated: ssl.SSLContext, anonymous: ssl.SSLContext) -> None:
    url = "https://localhost:8000/health/live"
    with urlopen(url, context=authenticated, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("status") != "alive":
        raise RuntimeError("Backend authenticated liveness response was invalid")
    _assert_anonymous_rejected(url, anonymous, "Backend")
    print("PASS: Backend accepts the coordinator certificate and rejects anonymous TLS")


def _check_party(url: str, party_id: int, authenticated: ssl.SSLContext, anonymous: ssl.SSLContext) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise RuntimeError(f"Party {party_id} control URL is not HTTPS")
    health_url = f"{url.rstrip('/')}/health"
    with urlopen(health_url, context=authenticated, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("status") != "healthy" or payload.get("party_id") != party_id:
        raise RuntimeError(f"Party {party_id} authenticated health response was invalid")
    _assert_anonymous_rejected(health_url, anonymous, f"Party {party_id}")
    print(f"PASS: Party {party_id} accepts the coordinator certificate and rejects anonymous TLS")


def main() -> int:
    try:
        if not settings.MPC_REQUIRE_TLS:
            raise RuntimeError("MPC_REQUIRE_TLS is not enabled")
        authenticated = _context(with_client_certificate=True)
        anonymous = _context(with_client_certificate=False)
        _check_backend(authenticated, anonymous)
        for party_id, url in enumerate(settings.party_urls):
            _check_party(url, party_id, authenticated, anonymous)
    except (OSError, URLError, ssl.SSLError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"FAIL: internal mTLS verification: {error}", file=sys.stderr)
        return 1
    print("Internal mTLS verification passed for the backend and all three parties.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
