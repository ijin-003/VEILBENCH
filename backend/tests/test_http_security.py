"""Security regression tests for the zero-budget authentication boundary."""
import pytest
from fastapi import HTTPException
from starlette.requests import Request

from backend.security.http_security import AuthThrottle, api_docs_enabled


def request(host: str = "203.0.113.12", forwarded: str = "198.51.100.77") -> Request:
    return Request({
        "type": "http",
        "method": "POST",
        "path": "/api/v1/accounts/login",
        "headers": [(b"x-forwarded-for", forwarded.encode())],
        "client": (host, 43111),
        "server": ("testserver", 80),
        "scheme": "http",
        "http_version": "1.1",
        "query_string": b"",
    })


@pytest.mark.asyncio
async def test_unknown_username_is_limited_and_window_expires():
    throttle = AuthThrottle()
    for i in range(throttle.USERNAME_LIMIT):
        await throttle.enforce(request(), action="login", username="NONEXISTENT", now=float(i))
    with pytest.raises(HTTPException) as caught:
        await throttle.enforce(request(), action="login", username="nonexistent", now=13.0)
    assert caught.value.status_code == 429
    assert caught.value.detail == "Too many requests. Please try again later."
    assert int(caught.value.headers["Retry-After"]) > 0
    await throttle.enforce(request(), action="login", username="nonexistent", now=901.0)


@pytest.mark.asyncio
async def test_ip_bucket_ignores_spoofed_forwarded_header():
    throttle = AuthThrottle()
    for i in range(throttle.SOURCE_LIMIT):
        await throttle.enforce(
            request(forwarded=f"198.51.100.{i % 255}"),
            action="login", username=f"user-{i}", now=0.0,
        )
    with pytest.raises(HTTPException) as caught:
        await throttle.enforce(request(forwarded="192.0.2.99"), action="login", username="fresh", now=0.0)
    assert caught.value.status_code == 429
    # A distinct transport address is not blocked by the first address's bucket.
    await throttle.enforce(request(host="203.0.113.99"), action="login", username="fresh", now=0.0)


@pytest.mark.asyncio
async def test_activation_is_throttled_separately_from_login():
    throttle = AuthThrottle()
    for i in range(throttle.USERNAME_LIMIT):
        await throttle.enforce(request(), action="activation", username="some-user", now=0.0)
    with pytest.raises(HTTPException) as caught:
        await throttle.enforce(request(), action="activation", username="some-user", now=0.0)
    assert caught.value.status_code == 429
    await throttle.enforce(request(), action="login", username="some-user", now=0.0)


@pytest.mark.asyncio
async def test_global_bucket_limits_username_rotation():
    throttle = AuthThrottle()
    throttle.GLOBAL_LIMIT = 5
    for i in range(5):
        await throttle.enforce(request(host=f"203.0.113.{i}"), action="login", username=f"user-{i}", now=0.0)
    with pytest.raises(HTTPException) as caught:
        await throttle.enforce(request(host="203.0.113.100"), action="login", username="another", now=0.0)
    assert caught.value.status_code == 429


def test_api_docs_are_explicitly_local_only(monkeypatch):
    monkeypatch.delenv("VEILBENCH_ENABLE_API_DOCS", raising=False)
    assert not api_docs_enabled("development")
    assert not api_docs_enabled("demo")
    assert not api_docs_enabled("production")
    monkeypatch.setenv("VEILBENCH_ENABLE_API_DOCS", "true")
    assert api_docs_enabled("development")
    assert not api_docs_enabled("demo")
    assert not api_docs_enabled("production")
