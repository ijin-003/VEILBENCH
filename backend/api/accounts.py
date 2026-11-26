"""Account workflow, kept separate from private party input endpoints."""
import secrets
import time
from datetime import timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from backend.config import settings
from backend.models.account import Account, LoginSession
from backend.models.session import BenchmarkSession
from backend.security.accounts import Db, current_account, admin_account, digest, hash_password, verify_password
from backend.security.tokens import issue_founder_token
from backend.security.http_security import auth_throttle

router = APIRouter(prefix="/accounts")
Member = Annotated[Account, Depends(current_account)]
Admin = Annotated[Account, Depends(admin_account)]
# Same password workload for unknown users, without persisting a usable credential.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(32))


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-z0-9][a-z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=128)


class Activation(Credentials):
    invitation: str = Field(min_length=20, max_length=128)


class Invite(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-z0-9][a-z0-9_.-]+$")
    session_id: str = Field(max_length=36)
    party_id: int = Field(ge=0, le=2)


def expiry(record: BenchmarkSession) -> int:
    return int(record.expires_at.replace(tzinfo=timezone.utc).timestamp())


async def record_failure(db, account):
    if account:
        account.failures += 1
        if account.failures >= 5:
            account.locked_until = int(time.time()) + 900
            account.failures = 0
        await db.commit()


@router.post("/login")
async def login(body: Credentials, response: Response, db: Db, request: Request):
    await auth_throttle.enforce(request, action="login", username=body.username)
    account = await db.scalar(select(Account).where(Account.username == body.username).with_for_update())
    now = int(time.time())
    valid = await run_in_threadpool(verify_password, body.password, account.password_hash if account and account.password_hash else _DUMMY_HASH)
    if not account or account.locked_until > now or not valid:
        if account and account.locked_until <= now:
            await record_failure(db, account)
        raise HTTPException(401, "Invalid credentials or account temporarily locked")
    account.failures = 0
    token = secrets.token_urlsafe(32)
    await db.execute(delete(LoginSession).where(LoginSession.expires_at <= now))
    db.add(LoginSession(token_hash=digest(token), username=account.username, expires_at=now + 3600))
    await db.commit()
    response.headers["Cache-Control"] = "no-store"
    return {"token": token, "role": account.role, "username": account.username}


@router.post("/activate")
async def activate(body: Activation, db: Db, request: Request):
    await auth_throttle.enforce(request, action="activation", username=body.username)
    account = await db.scalar(select(Account).where(Account.username == body.username).with_for_update())
    now = int(time.time())
    if not account or account.password_hash or not account.invitation_hash or account.invitation_expiry <= now or account.locked_until > now or not secrets.compare_digest(digest(body.invitation), account.invitation_hash):
        if account and account.locked_until <= now:
            await record_failure(db, account)
        raise HTTPException(400, "Invitation is invalid, expired, used, or temporarily locked")
    account.password_hash = await run_in_threadpool(hash_password, body.password)
    account.invitation_hash = None
    account.failures = 0
    await db.commit()
    return {"activated": True}


@router.post("/logout")
async def logout(db: Db, account: Member, authorization: Annotated[str, Header()]):
    await db.execute(delete(LoginSession).where(LoginSession.token_hash == digest(authorization[7:])))
    await db.commit()
    return {"logged_out": True}


@router.post("/invitations", status_code=201)
async def invite(body: Invite, response: Response, db: Db, admin: Admin):
    benchmark = await db.get(BenchmarkSession, body.session_id)
    if not benchmark or expiry(benchmark) <= int(time.time()) or benchmark.state != "created" or body.party_id in (benchmark.submitted_party_ids or []):
        raise HTTPException(409, "Choose an active session with an unassigned participant")
    token = secrets.token_urlsafe(32)
    db.add(Account(username=body.username, role="participant", invitation_hash=digest(token), invitation_expiry=expiry(benchmark), benchmark_id=body.session_id, party_id=body.party_id))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Username or session party already assigned") from None
    response.headers["Cache-Control"] = "no-store"
    return {"username": body.username, "invitation": token}


@router.get("/assignment")
async def assignment(response: Response, db: Db, account: Member):
    if account.role != "participant":
        raise HTTPException(403, "Participant access required")
    benchmark = await db.get(BenchmarkSession, account.benchmark_id)
    if not benchmark or expiry(benchmark) <= int(time.time()):
        raise HTTPException(410, "Your benchmark session has expired")
    response.headers["Cache-Control"] = "no-store"
    party_id = account.party_id
    return {
        "session_id": benchmark.id, "party_id": party_id,
        "capability": issue_founder_token(settings.founder_secrets[party_id], benchmark.id, party_id, expiry(benchmark)),
        "state": benchmark.state,
    }
