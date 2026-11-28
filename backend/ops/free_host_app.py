"""One-port academic deployment: coordinator and three separately scoped MPC party apps.

This is NOT an independently trusted deployment: all components share a process
and a hosting administrator. Salary input routes stay separate from coordinator
routes; the three real MPyC workers run as subprocesses when computing.
"""

import importlib.util
import os
import re
import secrets
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

_CONTROL_ROUTE = re.compile(r"^/sessions/[^/]+/(?:status|compute|result|shutdown)/?$")


class _HideUnauthenticatedPartyControlRoutes:
    """Return 404 for public control probes while retaining token-gated loopback calls."""

    def __init__(self, app: ASGIApp, control_token: str) -> None:
        if not control_token:
            raise RuntimeError("Free-host party control token is not configured")
        self.app = app
        self.control_token = control_token

    @staticmethod
    def _relative_path(scope: Scope) -> str:
        path = scope.get("path", "")
        root_path = scope.get("root_path", "")
        if root_path and path.startswith(root_path):
            return path[len(root_path):] or "/"
        return path

    def _has_valid_control_token(self, scope: Scope) -> bool:
        authorization = next(
            (
                value.decode("latin-1")
                for key, value in scope.get("headers", [])
                if key.lower() == b"authorization"
            ),
            "",
        )
        return authorization.startswith("Bearer ") and secrets.compare_digest(
            authorization[7:], self.control_token
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] == "http"
            and _CONTROL_ROUTE.fullmatch(self._relative_path(scope))
            and not self._has_valid_control_token(scope)
        ):
            await Response(status_code=404)(scope, receive, send)
            return
        await self.app(scope, receive, send)


def load_party_app(party_id: int):
    """Load party_service three times, each with its own module globals/state."""
    root = Path(__file__).resolve().parents[1]
    source = root / "mpc" / "party_service.py"
    module_name = f"veilbench_free_party_{party_id}"
    env_values = {
        "MPC_PARTY_ID": str(party_id),
        "MPC_PARTIES_COUNT": "3",
        "MPC_COORDINATOR_TOKEN": os.environ[f"MPC_NODE{party_id}_TOKEN"],
        "MPC_FOUNDER_TOKEN_SECRET": os.environ[f"MPC_FOUNDER_TOKEN_SECRET_{party_id}"],
        "MPC_PARTY_STATE_DB_PATH": f"/tmp/veilbench_party_{party_id}.sqlite3",
    }
    keys = {k: os.environ.get(k) for k in env_values}
    try:
        os.environ.update(env_values)
        spec = importlib.util.spec_from_file_location(module_name, source)
        if spec is None or spec.loader is None:
            raise RuntimeError("Unable to load MPC party module")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module.app
    finally:
        for key, original in keys.items():
            if original is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original


def create_app():
    # Import coordinator after start_free_host sets environment for demo mode.
    from backend.main import app as coordinator_app

    party_apps = [load_party_app(i) for i in range(3)]

    @asynccontextmanager
    async def lifespan(_app):
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(coordinator_app.router.lifespan_context(coordinator_app))
            for party_app in party_apps:
                await stack.enter_async_context(party_app.router.lifespan_context(party_app))
            yield

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    for i, party_app in enumerate(party_apps):
        app.mount(
            f"/party/{i}",
            _HideUnauthenticatedPartyControlRoutes(party_app, os.environ[f"MPC_NODE{i}_TOKEN"]),
        )
    # Must come last; main app handles /api/v1, /health, and root.
    app.mount("/", coordinator_app)
    return app


app = create_app()
