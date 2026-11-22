"""Password hashing and revocable, database-backed login sessions."""
import hashlib
import hmac
import secrets
import time
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.account import Account, LoginSession
from backend.services.database import get_database_session

Db = Annotated[AsyncSession, Depends(get_database_session)]


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password: str) -> str:
    if not 12 <= len(password) <= 128:
        raise ValueError("Choose a password between 12 and 128 characters")
    salt = secrets.token_hex(16)
    key = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
    return f"scrypt${salt}${key.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt, expected = encoded.split("$")
        if algorithm != "scrypt" or len(password) > 128:
            return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False


async def current_account(db: Db, authorization: Annotated[str | None, Header()] = None) -> Account:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Sign in to continue")
    login = await db.get(LoginSession, digest(authorization[7:]))
    if login is None or login.expires_at <= int(time.time()):
        raise HTTPException(401, "Your login has expired; sign in again")
    account = await db.get(Account, login.username)
    if account is None:
        raise HTTPException(401, "Invalid login")
    return account


async def admin_account(account: Annotated[Account, Depends(current_account)]) -> Account:
    if account.role != "admin":
        raise HTTPException(403, "Administrator access required")
    return account
