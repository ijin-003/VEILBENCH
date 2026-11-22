"""Small, bounded authentication throttle for the single-worker academic host.

The Render demo uses one ASGI worker, so a process-local limiter is shared by
login and invitation activation requests. This is defense in depth, not a
distributed or restart-persistent rate limiter. Do not claim production-grade
IP attribution behind an unverified reverse proxy.
"""
import asyncio
from collections import deque
from hashlib import sha256
import math
import os
import time

from fastapi import HTTPException, Request


def api_docs_enabled(environment: str) -> bool:
    """API schema routes require explicit opt-in and a local development mode."""
    return (
        environment.strip().lower() == "development"
        and os.environ.get("VEILBENCH_ENABLE_API_DOCS", "").strip().lower() in {"1", "true", "yes"}
    )


class AuthThrottle:
    """Atomic sliding-window limits. Requests are counted before authentication.

    Keys combine endpoint and (1) transport peer address, (2) username digest,
    and (3) total traffic. We deliberately ignore client-supplied Forwarded
    and X-Forwarded-For headers: those are spoofable without a validated proxy
    trust configuration. Behind a shared reverse proxy, the peer-address
    bucket may group multiple legitimate clients.
    """

    WINDOW_SECONDS = 15 * 60
    SOURCE_LIMIT = 60
    USERNAME_LIMIT = 12
    GLOBAL_LIMIT = 600

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._hits: dict[tuple[str, str], deque[float]] = {}
        self._requests = 0

    async def enforce(
        self, request: Request, *, action: str, username: str, now: float | None = None
    ) -> None:
        if action not in {"login", "activation"}:
            raise ValueError("Unsupported authentication throttle action")
        timestamp = time.monotonic() if now is None else now
        peer = request.client.host if request.client is not None else "unknown"
        # Unknown users and existing users must receive identical handling.
        username_key = sha256(username.strip().lower().encode("utf-8")).hexdigest()
        limits = (
            ((action, "peer:" + peer), self.SOURCE_LIMIT),
            ((action, "user:" + username_key), self.USERNAME_LIMIT),
            ((action, "global"), self.GLOBAL_LIMIT),
        )
        async with self._lock:
            self._requests += 1
            if self._requests % 128 == 0:
                self._prune(timestamp)
            retry_after = 0
            for key, limit in limits:
                hits = self._hits.get(key)
                if hits is not None:
                    while hits and hits[0] <= timestamp - self.WINDOW_SECONDS:
                        hits.popleft()
                if hits and len(hits) >= limit:
                    retry_after = max(
                        retry_after,
                        max(1, math.ceil(hits[0] + self.WINDOW_SECONDS - timestamp)),
                    )
            if retry_after:
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Please try again later.",
                    headers={"Retry-After": str(retry_after), "Cache-Control": "no-store"},
                )
            for key, _ in limits:
                self._hits.setdefault(key, deque()).append(timestamp)

    def _prune(self, timestamp: float) -> None:
        cutoff = timestamp - self.WINDOW_SECONDS
        for key, hits in list(self._hits.items()):
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if not hits:
                del self._hits[key]


auth_throttle = AuthThrottle()
