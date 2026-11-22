"""Isolated party service for direct founder submission and MPyC execution.

The coordinator never receives a salary. A founder browser posts directly to
this service using a short-lived, party-scoped capability; only a separate
control credential can inspect metadata or trigger computation.
"""

import asyncio
import json
import logging
import os
import secrets
import sqlite3
import sys
import time
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.mpc.config import MAX_SALARY, MIN_SALARY, MPC_TIMEOUT_SECONDS
from backend.mpc.exceptions import InvalidSalaryError
from backend.mpc.lifecycle import PartyLifecycle, PartyState
from backend.mpc.party_state_store import PartyStateStore
from backend.mpc.validation import validate_salary
from backend.security.tokens import FounderCapability, FounderTokenError, verify_founder_token

logger = logging.getLogger("veilbench.mpc.party_service")


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


PARTY_ID = int(os.environ.get("MPC_PARTY_ID", "0"))
PARTIES_COUNT = int(os.environ.get("MPC_PARTIES_COUNT", "3"))
BASE_PORT = int(os.environ.get("MPC_BASE_PORT", "11365"))
CONTROL_TOKEN = os.environ.get("MPC_COORDINATOR_TOKEN", "")
FOUNDER_TOKEN_SECRET = os.environ.get("MPC_FOUNDER_TOKEN_SECRET", "")
MPC_ENABLE_TLS = _env_flag("MPC_ENABLE_TLS", default=False)
MPC_REQUIRE_CLIENT_CERT = _env_flag("MPC_REQUIRE_CLIENT_CERT", default=False)
STATE_DB_PATH = os.environ.get(
    "MPC_PARTY_STATE_DB_PATH", f".state/party_{PARTY_ID}.sqlite3"
)
SESSION_CLEANUP_INTERVAL_SECONDS = max(
    5, int(os.environ.get("MPC_SESSION_CLEANUP_INTERVAL_SECONDS", "15"))
)
ALLOWED_ORIGINS = [
    item.strip()
    for item in os.environ.get(
        "MPC_PARTY_ALLOWED_ORIGINS", "https://localhost:3000,http://localhost:3000"
    ).split(",")
    if item.strip()
]


@dataclass
class PartySession:
    lifecycle: PartyLifecycle
    expires_at: int
    private_input: Optional[int] = None
    computation_result: Optional[dict] = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


_sessions: dict[str, PartySession] = {}
_runtime_lock = asyncio.Lock()
_submission_guard = asyncio.Lock()
_state_store = PartyStateStore(STATE_DB_PATH)


class SalaryInput(BaseModel):
    """Private field submitted only to this founder's assigned party."""

    salary: int = Field(..., strict=True, ge=MIN_SALARY, le=MAX_SALARY)


class PartyStatus(BaseModel):
    party_id: int
    session_id: str
    state: str
    input_submitted: bool
    uptime_seconds: float


class ComputationResult(BaseModel):
    party_id: int
    session_id: str
    aggregate_sum: int
    average_salary: float
    parties_count: int
    threshold: int


def _production_certificate_paths(party_id: int) -> list[Path]:
    return [
        Path("/app/certs/ca/ca.crt"),
        Path("/app/certs/control/control.crt"),
        Path("/app/certs/control/control.key"),
        Path("/app/.config/mpyc_ca.crt"),
        Path(f"/app/.config/party_{party_id}.crt"),
        Path(f"/app/.config/party_{party_id}.key"),
    ]


def validate_production_party_configuration() -> None:
    """Fail closed when a party starts with unsafe production settings."""
    errors: list[str] = []
    if PARTIES_COUNT != 3 or PARTY_ID not in range(3):
        errors.append("Production party configuration must identify one of exactly three parties")
    if not 1024 <= BASE_PORT <= 65533:
        errors.append("MPC_BASE_PORT must leave three valid non-privileged peer ports")
    if len(CONTROL_TOKEN) < 32:
        errors.append("MPC_COORDINATOR_TOKEN must be at least 32 characters")
    if len(FOUNDER_TOKEN_SECRET) < 32:
        errors.append("MPC_FOUNDER_TOKEN_SECRET must be at least 32 characters")
    if not MPC_ENABLE_TLS:
        errors.append("MPC_ENABLE_TLS must be enabled in production")
    if not MPC_REQUIRE_CLIENT_CERT:
        errors.append("MPC_REQUIRE_CLIENT_CERT must be enabled in production")
    if not ALLOWED_ORIGINS or any(
        origin == "*" or not origin.startswith("https://") for origin in ALLOWED_ORIGINS
    ):
        errors.append("MPC_PARTY_ALLOWED_ORIGINS must contain exact HTTPS origins")
    if any("localhost" in origin for origin in ALLOWED_ORIGINS):
        errors.append("MPC_PARTY_ALLOWED_ORIGINS must not contain localhost in production")

    certificate_paths = _production_certificate_paths(PARTY_ID)
    for path in certificate_paths:
        if not path.is_file():
            errors.append(f"Required production certificate file is missing: {path}")
    for path in (Path("/app/certs/control/control.key"), Path(f"/app/.config/party_{PARTY_ID}.key")):
        if path.is_file() and os.name == "posix" and path.stat().st_mode & 0o077:
            errors.append(f"Production private key permissions are too broad: {path}")

    state_path = Path(STATE_DB_PATH)
    if not state_path.is_absolute():
        errors.append("MPC_PARTY_STATE_DB_PATH must be absolute in production")
    elif not state_path.parent.is_dir() or not os.access(state_path.parent, os.W_OK):
        errors.append("MPC party state directory must exist and be writable")

    if errors:
        raise RuntimeError("; ".join(errors))


def _verify_control_token(authorization: str | None) -> None:
    if not CONTROL_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Party control authentication is not configured",
        )
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing control credential")
    if not secrets.compare_digest(authorization[7:], CONTROL_TOKEN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid control credential")


def _verify_founder_capability(authorization: str | None, session_id: str) -> FounderCapability:
    if not FOUNDER_TOKEN_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Founder submission authentication is not configured",
        )
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing founder capability")
    try:
        return verify_founder_token(authorization[7:], FOUNDER_TOKEN_SECRET, session_id, PARTY_ID)
    except FounderTokenError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid founder capability") from error


def _session(session_id: str, create: bool = False, expires_at: int | None = None) -> PartySession:
    state = _sessions.get(session_id)
    if state is None and create:
        state = PartySession(
            lifecycle=PartyLifecycle(party_id=PARTY_ID, session_id=session_id),
            expires_at=int(expires_at or 0),
        )
        _sessions[session_id] = state
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown benchmark session")
    return state


async def _cleanup_expired_sessions(now: int | None = None) -> int:
    """Purge expired volatile inputs and their now-unneeded replay guards."""
    current_time = int(time.time()) if now is None else int(now)
    removed = 0
    for session_id, party_session in list(_sessions.items()):
        if party_session.expires_at > current_time:
            continue
        async with party_session.lock:
            if _sessions.get(session_id) is not party_session:
                continue
            was_submitted = party_session.lifecycle.input_submitted
            party_session.private_input = None
            party_session.computation_result = None
            try:
                _state_store.set_state(
                    session_id,
                    "EXPIRED",
                    expires_at=party_session.expires_at,
                    input_submitted=was_submitted,
                )
            except sqlite3.Error:
                logger.exception("Party %d could not persist expiry for session %s", PARTY_ID, session_id)
                continue
            _sessions.pop(session_id, None)
            removed += 1
    try:
        _state_store.delete_expired(current_time)
    except sqlite3.Error:
        logger.exception("Party %d could not prune expired replay guards", PARTY_ID)
    return removed


async def _expiration_loop() -> None:
    while True:
        await _cleanup_expired_sessions()
        await asyncio.sleep(SESSION_CLEANUP_INTERVAL_SECONDS)


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """Recover volatile sessions and periodically purge expired private data."""
    if os.environ.get("ENVIRONMENT", "development").lower() == "production":
        validate_production_party_configuration()
    recovered = _state_store.recover_incomplete()
    if recovered:
        logger.warning("Party %d marked %d interrupted session(s) as failed after restart", PARTY_ID, recovered)
    cleanup_task = asyncio.create_task(_expiration_loop(), name=f"party-{PARTY_ID}-session-cleanup")
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task
        for party_session in _sessions.values():
            party_session.private_input = None
            party_session.computation_result = None


app = FastAPI(
    title=f"VEILBENCH MPC Party {PARTY_ID}",
    version="0.2.0",
    description="Isolated MPyC party. It never exposes another party's input.",
    lifespan=_lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(RequestValidationError)
async def invalid_request(_request, _error):
    """Never echo a rejected private salary in validation responses."""
    return JSONResponse(status_code=422, content={"detail": "Invalid request"})


@app.get("/health")
async def health_check() -> dict[str, object]:
    """No session or private-input state is disclosed by the health endpoint."""
    return {"status": "healthy", "party_id": PARTY_ID, "mpyc_tls_enabled": MPC_ENABLE_TLS}


@app.post("/sessions/{session_id}/input")
async def submit_input(
    session_id: str,
    payload: SalaryInput,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    """Accept one founder's salary directly, then retain it only in memory."""
    capability = _verify_founder_capability(authorization, session_id)
    if capability.expires_at <= int(time.time()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid founder capability")
    try:
        validated = validate_salary(payload.salary)
    except InvalidSalaryError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid salary") from error

    # The persistent unique insert is the source of truth for one-time use.
    # It also prevents replay after a process restart or memory cleanup.
    async with _submission_guard:
        try:
            existing_state = _state_store.claim_submission(session_id, capability.expires_at)
        except sqlite3.Error as error:
            logger.exception("Party %d could not reserve founder capability for session %s", PARTY_ID, session_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Party submission storage is unavailable",
            ) from error
        if existing_state is not None:
            if existing_state in {"FAILED", "SHUTDOWN", "EXPIRED"}:
                raise HTTPException(status_code=status.HTTP_410_GONE, detail="Benchmark session has been cleared")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Input already submitted")
        party_session = _session(session_id, create=True, expires_at=capability.expires_at)

    async with party_session.lock:
        try:
            party_session.lifecycle.mark_input_submitted()
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Input already submitted") from error
        party_session.private_input = validated
        if party_session.lifecycle.state == PartyState.INITIALIZING:
            party_session.lifecycle.transition(PartyState.WAITING_FOR_PARTICIPANTS)

    logger.info("Party %d accepted a private input for session %s", PARTY_ID, session_id)
    return {"status": "accepted", "party_id": PARTY_ID, "input_submitted": True}


@app.get("/sessions/{session_id}/status", response_model=PartyStatus)
async def get_status(
    session_id: str, authorization: str | None = Header(default=None)
) -> PartyStatus:
    _verify_control_token(authorization)
    party_session = _sessions.get(session_id)
    if party_session is not None:
        return PartyStatus(**party_session.lifecycle.to_dict())

    try:
        stored = _state_store.get(session_id)
    except sqlite3.Error as error:
        raise HTTPException(status_code=503, detail="Party session storage is unavailable") from error
    if stored is None:
        return PartyStatus(
            party_id=PARTY_ID,
            session_id=session_id,
            state="INITIALIZING",
            input_submitted=False,
            uptime_seconds=0,
        )
    stored_state = str(stored["state"])
    if stored_state in {"SUBMITTED", "COMPUTING", "COMPLETED"}:
        stored_state = "FAILED"  # Volatile input/result cannot survive a process restart.
    return PartyStatus(
        party_id=PARTY_ID,
        session_id=session_id,
        state=stored_state,
        input_submitted=bool(stored["input_submitted"]),
        uptime_seconds=0,
    )


@app.post("/sessions/{session_id}/compute", response_model=ComputationResult)
async def trigger_computation(
    session_id: str, authorization: str | None = Header(default=None)
) -> ComputationResult:
    """Start the real MPyC subprocess after coordinator metadata checks."""
    _verify_control_token(authorization)
    party_session = _session(session_id)
    async with party_session.lock:
        if party_session.private_input is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No private input submitted")
        if party_session.computation_result is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Computation already completed")
        try:
            if party_session.lifecycle.state == PartyState.WAITING_FOR_PARTICIPANTS:
                party_session.lifecycle.transition(PartyState.READY)
            _state_store.set_state(
                session_id, "COMPUTING", expires_at=party_session.expires_at, input_submitted=True
            )
        except sqlite3.Error as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Party session storage is unavailable",
            ) from error
        try:
            party_session.lifecycle.transition(PartyState.COMPUTING)
        except ValueError as error:
            with suppress(sqlite3.Error):
                _state_store.set_state(
                    session_id, "FAILED", expires_at=party_session.expires_at, input_submitted=True
                )
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid session state") from error

        private_input = party_session.private_input
        try:
            # All three nodes use the same fixed MPyC ports, so a party allows
            # only one active computation at a time.
            async with _runtime_lock:
                result = await _run_mpyc_computation(private_input)
            _state_store.set_state(
                session_id, "COMPLETED", expires_at=party_session.expires_at, input_submitted=True
            )
            party_session.computation_result = result
            party_session.lifecycle.transition(PartyState.COMPLETED)
            return ComputationResult(session_id=session_id, **result)
        except Exception:
            if party_session.lifecycle.state == PartyState.COMPUTING:
                party_session.lifecycle.transition(PartyState.FAILED)
            with suppress(sqlite3.Error):
                _state_store.set_state(
                    session_id, "FAILED", expires_at=party_session.expires_at, input_submitted=True
                )
            logger.exception("Party %d MPC computation failed for session %s", PARTY_ID, session_id)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="MPC computation did not complete",
            ) from None
        finally:
            # The process has received its input. Do not retain salary values
            # after either a success or a failure.
            party_session.private_input = None


@app.get("/sessions/{session_id}/result", response_model=ComputationResult)
async def get_result(
    session_id: str, authorization: str | None = Header(default=None)
) -> ComputationResult:
    _verify_control_token(authorization)
    party_session = _session(session_id)
    if party_session.computation_result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No aggregate result is available")
    return ComputationResult(session_id=session_id, **party_session.computation_result)


@app.post("/sessions/{session_id}/shutdown")
async def shutdown_session(
    session_id: str,
    authorization: str | None = Header(default=None),
    expires_at: int | None = Query(default=None, ge=0),
) -> dict[str, object]:
    """Idempotently purge volatile data and retain a durable replay tombstone."""
    _verify_control_token(authorization)
    party_session = _sessions.get(session_id)

    if party_session is None:
        try:
            _state_store.set_state(session_id, "SHUTDOWN", expires_at=expires_at)
        except sqlite3.Error as error:
            raise HTTPException(status_code=503, detail="Party session storage is unavailable") from error
        return {"status": "already_cleared", "party_id": PARTY_ID}

    async with party_session.lock:
        if party_session.lifecycle.state != PartyState.SHUTDOWN:
            try:
                party_session.lifecycle.transition(PartyState.SHUTDOWN)
            except ValueError:
                if party_session.lifecycle.state == PartyState.COMPUTING:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Cannot clear an active computation",
                    )
                party_session.lifecycle.transition(PartyState.FAILED)
                party_session.lifecycle.transition(PartyState.SHUTDOWN)

        try:
            _state_store.set_state(
                session_id,
                "SHUTDOWN",
                expires_at=expires_at or party_session.expires_at,
                input_submitted=party_session.lifecycle.input_submitted,
            )
        except sqlite3.Error as error:
            raise HTTPException(status_code=503, detail="Party session storage is unavailable") from error
        party_session.private_input = None
        party_session.computation_result = None

    _sessions.pop(session_id, None)
    logger.info("Party %d cleared session %s", PARTY_ID, session_id)
    return {"status": "cleared", "party_id": PARTY_ID}


async def _run_mpyc_computation(salary: int) -> dict:
    """Launch a real, independently-addressed MPyC party process."""
    if PARTIES_COUNT != 3 or PARTY_ID not in range(PARTIES_COUNT):
        raise RuntimeError("Invalid MPC party configuration")

    command = [
        sys.executable,
        "-m",
        "backend.mpc.party_runner",
        "-M",
        str(PARTIES_COUNT),
        "-I",
        str(PARTY_ID),
        "--base-port",
        str(BASE_PORT),
    ]
    if MPC_ENABLE_TLS:
        required_files = [
            Path(".config") / "mpyc_ca.crt",
            Path(".config") / f"party_{PARTY_ID}.crt",
            Path(".config") / f"party_{PARTY_ID}.key",
        ]
        if not all(path.is_file() for path in required_files):
            raise RuntimeError("MPyC TLS material is not mounted")
        command.extend(["-T", "1", "--ssl"])

    for index in range(PARTIES_COUNT):
        hostname = os.environ.get(f"MPC_PARTY_{index}_HOST", f"veilbench-mpc-node{index}")
        port = BASE_PORT + index
        command.extend(["-P", f":{port}" if index == PARTY_ID else f"{hostname}:{port}"])

    process = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    communication = asyncio.create_task(
        process.communicate(json.dumps(salary).encode("utf-8") + b"\n")
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            asyncio.shield(communication), timeout=MPC_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError as error:
        with suppress(ProcessLookupError):
            process.kill()
        # Keep the communicate task alive while the killed process is reaped
        # and both pipes are drained. This avoids orphaned Proactor transports
        # on Windows when wait_for times out.
        try:
            await asyncio.wait_for(communication, timeout=5)
        except asyncio.TimeoutError:
            communication.cancel()
            await asyncio.gather(communication, return_exceptions=True)
            await process.wait()
        raise TimeoutError("MPyC computation timed out") from error

    output = stdout.decode("utf-8", errors="replace")
    if process.returncode != 0 or "__MPC_RESULT_START__" not in output:
        # Deliberately do not return subprocess stderr to callers or logs.
        _ = stderr
        raise RuntimeError("MPyC party process failed")
    try:
        result_json = output.split("__MPC_RESULT_START__", 1)[1].split("__MPC_RESULT_END__", 1)[0]
        result = json.loads(result_json)
        return {
            "party_id": PARTY_ID,
            "aggregate_sum": int(result["aggregate_sum"]),
            "average_salary": float(result["average_salary"]),
            "parties_count": int(result["parties_count"]),
            "threshold": int(result["threshold"]),
        }
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeError("MPyC party process returned an invalid result") from error
