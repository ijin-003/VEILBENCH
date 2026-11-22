"""Short-lived, signed founder submission capabilities."""

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass


class FounderTokenError(ValueError):
    """Raised when a founder submission capability is invalid or expired."""


@dataclass(frozen=True)
class FounderCapability:
    session_id: str
    party_id: int
    expires_at: int


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise ValueError("Invalid Base64 value")

    if not all(
        ch.isascii() and (ch.isalnum() or ch in "-_")
        for ch in value
    ):
        raise ValueError("Invalid Base64 characters")

    decoded = base64.b64decode(
        value + "=" * (-len(value) % 4),
        altchars=b"-_",
        validate=True,
    )

    # Reject alternative, non-canonical encodings.
    if _b64encode(decoded) != value:
        raise ValueError("Non-canonical Base64 encoding")

    return decoded


def issue_founder_token(secret: str, session_id: str, party_id: int, expires_at: int) -> str:
    if not secret:
        raise FounderTokenError("Founder token signing secret is not configured")
    payload = {
        "exp": int(expires_at),
        "party_id": int(party_id),
        "scope": "founder-submit",
        "session_id": session_id,
    }
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    encoded_payload = _b64encode(payload_bytes)
    signature = hmac.new(secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded_payload}.{_b64encode(signature)}"


def verify_founder_token(
    token: str,
    secret: str,
    expected_session_id: str,
    expected_party_id: int,
    now: int | None = None,
) -> FounderCapability:
    """Validate an exact party/session-scoped capability in constant time."""
    if not secret:
        raise FounderTokenError("Founder token verification secret is not configured")
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        supplied_signature = _b64decode(encoded_signature)
        expected_signature = hmac.new(
            secret.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(supplied_signature, expected_signature):
            raise FounderTokenError("Invalid founder capability")
        payload = json.loads(_b64decode(encoded_payload))
        expires_at = int(payload["exp"])
        party_id = int(payload["party_id"])
        session_id = str(payload["session_id"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        if isinstance(error, FounderTokenError):
            raise
        raise FounderTokenError("Malformed founder capability") from error

    current_time = int(time.time()) if now is None else int(now)
    if payload.get("scope") != "founder-submit":
        raise FounderTokenError("Invalid founder capability scope")
    if expires_at <= current_time:
        raise FounderTokenError("Founder capability has expired")
    if session_id != expected_session_id or party_id != expected_party_id:
        raise FounderTokenError("Founder capability is not valid for this party session")
    return FounderCapability(session_id=session_id, party_id=party_id, expires_at=expires_at)
