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
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.mpc.config import MAX_SALARY, MIN_SALARY, MPC_TIMEOUT_SECONDS
from backend.mpc.exceptions import InvalidSalaryError
from backend.mpc.lifecycle import PartyLifecycle, PartyState
from backend.mpc.validation import validate_salary
from backend.security.tokens import FounderTokenError, verify_founder_token

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
    private_input: Optional[int] = None
    computation_result: Optional[dict] = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


_sessions: dict[str, PartySession] = {}
_runtime_lock = asyncio.Lock()

app = FastAPI(
    title=f"VEILBENCH MPC Party {PARTY_ID}",
    version="0.2.0",
    description="Isolated MPyC party. It never exposes another party's input.",
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


def _verify_founder_capability(authorization: str | None, session_id: str) -> None:
    if not FOUNDER_TOKEN_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Founder submission authentication is not configured",
        )
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing founder capability")
    try:
        verify_founder_token(authorization[7:], FOUNDER_TOKEN_SECRET, session_id, PARTY_ID)
    except FounderTokenError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid founder capability") from error


def _session(session_id: str, create: bool = False) -> PartySession:
    state = _sessions.get(session_id)
    if state is None and create:
        state = PartySession(lifecycle=PartyLifecycle(party_id=PARTY_ID, session_id=session_id))
        _sessions[session_id] = state
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown benchmark session")
    return state


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
    _verify_founder_capability(authorization, session_id)
    try:
        validated = validate_salary(payload.salary)
    except InvalidSalaryError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid salary") from error

    party_session = _session(session_id, create=True)
    async with party_session.lock:
        if party_session.lifecycle.state == PartyState.SHUTDOWN:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Benchmark session has been cleared")
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
    if session_id not in _sessions:
        return PartyStatus(party_id=PARTY_ID, session_id=session_id,
                           state="INITIALIZING", input_submitted=False, uptime_seconds=0)
    return PartyStatus(**_session(session_id).lifecycle.to_dict())


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
            party_session.lifecycle.transition(PartyState.COMPUTING)
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid session state") from error

        private_input = party_session.private_input
        try:
            # All three nodes use the same fixed MPyC ports, so a party allows
            # only one active computation at a time.
            async with _runtime_lock:
                result = await _run_mpyc_computation(private_input)
            party_session.computation_result = result
            party_session.lifecycle.transition(PartyState.COMPLETED)
            return ComputationResult(session_id=session_id, **result)
        except Exception:
            if party_session.lifecycle.state == PartyState.COMPUTING:
                party_session.lifecycle.transition(PartyState.FAILED)
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
    session_id: str, authorization: str | None = Header(default=None)
) -> dict[str, object]:
    """Purge the in-memory input and aggregate after the coordinator persists it."""
    _verify_control_token(authorization)
    party_session = _session(session_id)
    async with party_session.lock:
        if party_session.lifecycle.state != PartyState.SHUTDOWN:
            try:
                party_session.lifecycle.transition(PartyState.SHUTDOWN)
            except ValueError:
                # A computing session cannot be cleanly stopped mid-process;
                # this endpoint is only called after the process returns.
                party_session.lifecycle.transition(PartyState.FAILED)
                party_session.lifecycle.transition(PartyState.SHUTDOWN)
        party_session.private_input = None
        party_session.computation_result = None
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
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(json.dumps(salary).encode("utf-8") + b"\n"),
            timeout=MPC_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as error:
        process.kill()
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
