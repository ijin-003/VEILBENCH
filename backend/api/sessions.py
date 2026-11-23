"""Coordinator management API; it intentionally contains no salary endpoint."""

import secrets
import time
from datetime import datetime, timezone
from typing import Literal
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import select, func
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models import BenchmarkSession
from backend.mpc.distributed_coordinator import DistributedCoordinator
from backend.mpc.exceptions import (
    ConfigurationError,
    MPCExecutionFailed,
    MPCRecoveryRequired,
    MPCTimeoutError,
    PartyDisconnectedError,
)
from backend.security.tokens import issue_founder_token
from backend.security.accounts import current_account
from backend.services.database import get_database_session
from backend.services.session_service import (
    SessionLifecycleError,
    compute_session,
    create_session,
    get_session,
    refresh_submission_state,
    recover_session,
)

router = APIRouter(prefix="/sessions")


class CreateSessionRequest(BaseModel):
    ttl_minutes: int = Field(default=30, ge=5, le=120)


class FounderInvite(BaseModel):
    party_id: int
    submission_page: str
    submission_api: str
    capability_token: str


class SessionResult(BaseModel):
    aggregate_sum: int
    average_salary: float


class SessionView(BaseModel):
    session_id: str
    state: str
    created_at: datetime
    expires_at: datetime
    submitted_party_ids: list[int]
    result: SessionResult | None = None
    failure_reason: str | None = None


class CreatedSession(SessionView):
    founder_invites: list[FounderInvite]


class SessionDirectory(BaseModel):
    sessions: list[SessionView]
    total: int


def _as_view(record: BenchmarkSession) -> SessionView:
    result = None
    if record.aggregate_sum is not None and record.average_salary is not None:
        result = SessionResult(aggregate_sum=record.aggregate_sum, average_salary=record.average_salary)
    return SessionView(
        session_id=record.id,
        state=record.state,
        created_at=record.created_at,
        expires_at=record.expires_at,
        submitted_party_ids=sorted(record.submitted_party_ids or []),
        result=result,
        failure_reason=record.failure_reason,
    )


async def require_management_token(
    provided: Annotated[str | None, Header(alias="X-VEILBENCH-Admin-Token")] = None,
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_database_session),
) -> None:
    if authorization:
        account = await current_account(db, authorization)
        if account.role != "admin":
            raise HTTPException(403, "Administrator access required")
        return
    if not settings.COORDINATOR_ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Coordinator management authentication is not configured",
        )
    if provided is None or not secrets.compare_digest(provided, settings.COORDINATOR_ADMIN_TOKEN):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid management credential")


ManagementAccess = Annotated[None, Depends(require_management_token)]
DatabaseSession = Annotated[AsyncSession, Depends(get_database_session)]


def _coordinator() -> DistributedCoordinator:
    try:
        settings.validate_mpc_runtime()
        return DistributedCoordinator(
            settings.party_urls,
            settings.party_control_tokens,
            ca_cert_path=settings.MPC_CA_CERT_PATH,
            client_cert_path=settings.MPC_CLIENT_CERT_PATH,
            client_key_path=settings.MPC_CLIENT_KEY_PATH,
            require_tls=settings.MPC_REQUIRE_TLS,
            timeout=settings.MPC_TIMEOUT_SECONDS,
        )
    except (RuntimeError, ConfigurationError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MPC session runtime is not configured",
        ) from error


def _session_or_404_error(error: Exception) -> HTTPException:
    if isinstance(error, LookupError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benchmark session was not found")
    if isinstance(error, SessionLifecycleError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(
        error,
        (MPCTimeoutError, PartyDisconnectedError, ConfigurationError, MPCExecutionFailed, MPCRecoveryRequired),
    ):
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="An MPC party is unavailable")
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Session operation failed")


@router.post("", response_model=CreatedSession, status_code=status.HTTP_201_CREATED)
async def start_session(
    request: CreateSessionRequest,
    response: Response,
    _: ManagementAccess,
    db: DatabaseSession,
    authorization: Annotated[str | None, Header()] = None,
) -> CreatedSession:
    # This response contains three short-lived founder capabilities. Never let
    # browsers, reverse proxies, or shared caches retain the invitation payload.
    response.headers["Cache-Control"] = "no-store, no-cache, max-age=0, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    _coordinator()  # Fail before persisting an unusable session.
    ttl_seconds = min(request.ttl_minutes * 60, settings.SESSION_TTL_SECONDS)
    record = await create_session(db, ttl_seconds)
    expires_at = int(record.expires_at.timestamp())
    invites = [
        FounderInvite(
            party_id=party_id,
            submission_page=f"{settings.FRONTEND_PUBLIC_URL.rstrip('/')}/submit/{record.id}/{party_id}",
            submission_api=f"{settings.MPC_PARTY_PUBLIC_URLS[party_id].rstrip('/')}/sessions/{record.id}/input",
            capability_token="" if isinstance(authorization, str) else issue_founder_token(
                settings.founder_secrets[party_id], record.id, party_id, expires_at
            ),
        )
        for party_id in range(3)
    ]
    return CreatedSession(**_as_view(record).model_dump(), founder_invites=invites)


@router.get("", response_model=SessionDirectory)
async def list_sessions(
    response: Response,
    _: ManagementAccess,
    db: DatabaseSession,
    scope: Literal["active", "all"] = "active",
    offset: int = 0,
    limit: int = 50,
) -> SessionDirectory:
    """Return bounded session metadata for the administrator's session browser.

    This endpoint intentionally neither contacts party services nor returns
    salary inputs, tokens, or private shares. Poll individual selected session
    status separately to obtain current submission metadata.
    """
    if offset < 0 or not 1 <= limit <= 100:
        raise HTTPException(422, "Use offset >= 0 and limit between 1 and 100")
    query = select(BenchmarkSession)
    count_query = select(func.count()).select_from(BenchmarkSession)
    if scope == "active":
        active = (
            BenchmarkSession.expires_at > datetime.now(timezone.utc),
            BenchmarkSession.state.in_(("created", "ready", "computing")),
        )
        query = query.where(*active)
        count_query = count_query.where(*active)
    total = await db.scalar(count_query)
    records = (await db.scalars(
        query.order_by(BenchmarkSession.created_at.desc(), BenchmarkSession.id.desc())
        .offset(offset).limit(limit)
    )).all()
    response.headers["Cache-Control"] = "no-store"
    return SessionDirectory(total=total or 0, sessions=[_as_view(record) for record in records])


@router.get("/{session_id}", response_model=SessionView)
async def session_status(
    session_id: str,
    _: ManagementAccess,
    db: DatabaseSession,
) -> SessionView:
    try:
        record = await get_session(db, session_id)
        if record.state not in ("completed", "failed", "expired"):
            record = await refresh_submission_state(db, record, _coordinator())
        return _as_view(record)
    except HTTPException:
        raise
    except Exception as error:
        raise _session_or_404_error(error) from error


@router.post("/{session_id}/compute", response_model=SessionView)
async def run_session(
    session_id: str,
    _: ManagementAccess,
    db: DatabaseSession,
    response: Response,
) -> SessionView:
    """Expose authenticated coordinator request duration, never private inputs.

    The measurement includes coordinator status checks, the real three-party
    computation and database finalization. It excludes founder onboarding,
    browser/network transit and possible Render cold starts.
    """
    started = time.perf_counter()
    response.headers["Cache-Control"] = "no-store"
    try:
        record = await get_session(db, session_id)
        if record.state not in ("completed", "failed", "expired"):
            record = await refresh_submission_state(db, record, _coordinator())
        record = await compute_session(db, record, _coordinator())
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        response.headers["Server-Timing"] = f"coordinator-compute;dur={elapsed_ms:.2f}"
        return _as_view(record)
    except HTTPException:
        raise
    except Exception as error:
        raise _session_or_404_error(error) from error


@router.post("/{session_id}/recover", response_model=SessionView)
async def recover_stuck_session(
    session_id: str,
    _: ManagementAccess,
    db: DatabaseSession,
) -> SessionView:
    """Retry party shutdown and release a COMPUTING barrier only when confirmed."""
    try:
        record = await get_session(db, session_id)
        record = await recover_session(db, record, _coordinator())
        return _as_view(record)
    except HTTPException:
        raise
    except Exception as error:
        raise _session_or_404_error(error) from error
