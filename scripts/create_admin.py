"""Provision an administrator without putting passwords in arguments or logs."""
import asyncio
import getpass
from backend.api.accounts import Credentials
from backend.models.account import Account
from backend.security.accounts import hash_password
from backend.services.database import database


async def main():
    username = input("Admin username: ").strip().lower()
    password = getpass.getpass("Password (12–128 characters): ")
    if password != getpass.getpass("Confirm password: "):
        raise SystemExit("Passwords do not match")
    credentials = Credentials(username=username, password=password)
    await database.start()
    try:
        async for db in database.get_session():
            if await db.get(Account, username):
                raise SystemExit("Username already exists; no changes made")
            db.add(Account(username=username, role="admin", password_hash=hash_password(credentials.password)))
            await db.commit()
        print("Administrator created")
    finally:
        await database.stop()


if __name__ == "__main__":
    asyncio.run(main())
