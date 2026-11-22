"""Metadata-only lifecycle management for a VEILBENCH benchmark session."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import BenchmarkSession, SessionState
from backend.mpc.distributed_coordinator import DistributedCoordinator
from backend.mpc.exceptions import MPCExecutionFailed


class SessionLifecycleError(RuntimeError):
    """A requested transition is not valid for the benchmark session."""


async def create_session(db: AsyncSession, ttl_seconds: int) -> BenchmarkSession:
    now = datetime.now(timezone.utc)
    record = BenchmarkSession(
        id=str(uuid4()),
        state=SessionState.CREATED.value,
        created_at=now,
        expires_at=now + timedelta(seconds=ttl_seconds),
        submitted_party_ids=[],
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_session(db: AsyncSession, session_id: str) -> BenchmarkSession:
    record = await db.scalar(select(BenchmarkSession).where(BenchmarkSession.id == session_id))
    if record is None:
        raise LookupError("Benchmark session was not found")
    return record


async def _ensure_not_expired(db: AsyncSession, record: BenchmarkSession) -> None:
    if record.expires_at <= datetime.now(timezone.utc):
        record.state = SessionState.EXPIRED.value
        await db.commit()
        raise SessionLifecycleError("Benchmark session has expired")


async def refresh_submission_state(
    db: AsyncSession, record: BenchmarkSession, coordinator: DistributedCoordinator
) -> BenchmarkSession:
    await db.execute(text("SELECT pg_advisory_xact_lock(74012001)"))
    await db.refresh(record)
    if record.state not in (SessionState.CREATED.value, SessionState.READY.value):
        await db.commit()
        return record
    await _ensure_not_expired(db, record)
    statuses = await coordinator.get_statuses(record.id)
    terminal_party_states = {"FAILED", "SHUTDOWN", "EXPIRED"}
    if any(str(item.get("state", "")).upper() in terminal_party_states for item in statuses):
        record.state = SessionState.FAILED.value
        record.failure_reason = (
            "An MPC party lost its volatile session state. Create a new benchmark session."
        )
        await db.commit()
        await db.refresh(record)
        return record

    submitted = sorted(
        item["party_id"]
        for item in statuses
        if item.get("input_submitted") is True
        and str(item.get("state", "")).upper() in {"WAITING_FOR_PARTICIPANTS", "READY"}
    )
    record.submitted_party_ids = submitted
    if len(submitted) == 3 and record.state == SessionState.CREATED.value:
        record.state = SessionState.READY.value
    await db.commit()
    await db.refresh(record)
    return record


async def compute_session(
    db: AsyncSession, record: BenchmarkSession, coordinator: DistributedCoordinator
) -> BenchmarkSession:
    # Serialize admission across all coordinator workers. A persisted COMPUTING
    # row blocks other runs even if the coordinator crashes after this commit.
    # PostgreSQL is required by this service; do not replace this with a local lock.
    await db.execute(text("SELECT pg_advisory_xact_lock(74012001)"))
    await db.refresh(record)
    if record.state == SessionState.COMPLETED.value:
        await db.commit()
        return record
    if record.state != SessionState.READY.value:
        await db.rollback()
        raise SessionLifecycleError("Session is not ready for computation")
    active = await db.scalar(select(BenchmarkSession.id).where(
        BenchmarkSession.state == SessionState.COMPUTING.value
    ).limit(1))
    if active is not None:
        await db.rollback()
        raise SessionLifecycleError("Another computation is active or requires recovery")
    await _ensure_not_expired(db, record)
    if sorted(record.submitted_party_ids) != [0, 1, 2]:
        raise SessionLifecycleError("All three founders must submit before computation")

    record.state = SessionState.COMPUTING.value
    await db.commit()
    try:
        result = await coordinator.execute_protocol(
            record.id, expires_at=int(record.expires_at.timestamp())
        )
    except MPCExecutionFailed:
        # All three parties confirmed cleanup, so the failed attempt no longer
        # needs to hold the global computation-admission barrier.
        record.state = SessionState.FAILED.value
        record.failure_reason = "MPC computation failed; all party sessions were cleared"
        await db.commit()
        raise
    except BaseException:
        # Fail closed if cleanup could not be confirmed or the coordinator was
        # interrupted. An administrator can retry the idempotent shutdown.
        record.failure_reason = "MPC recovery required before another computation"
        await db.commit()
        raise

    record.aggregate_sum = int(result["aggregate_sum"])
    record.average_salary = float(result["average_salary"])
    record.state = SessionState.COMPLETED.value
    record.failure_reason = None
    await db.commit()
    await db.refresh(record)
    return record


async def recover_session(
    db: AsyncSession, record: BenchmarkSession, coordinator: DistributedCoordinator
) -> BenchmarkSession:
    """Release a stuck COMPUTING barrier only after every party confirms shutdown."""
    await db.execute(text("SELECT pg_advisory_xact_lock(74012001)"))
    await db.refresh(record)
    if record.state != SessionState.COMPUTING.value:
        await db.rollback()
        raise SessionLifecycleError("Only a session awaiting MPC recovery can be recovered")

    try:
        await coordinator.shutdown_session(
            record.id, expires_at=int(record.expires_at.timestamp())
        )
    except BaseException:
        record.failure_reason = "MPC recovery is still required; party cleanup was not confirmed"
        await db.commit()
        raise

    record.state = SessionState.FAILED.value
    record.failure_reason = "MPC session recovered after all parties confirmed cleanup"
    await db.commit()
    await db.refresh(record)
    return record
