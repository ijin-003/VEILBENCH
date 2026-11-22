"""Start VEILBENCH's zero-cost managed-host proof of concept on one HTTP port."""
import asyncio
import os
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def configure():
    port = int(os.environ.get("PORT", "10000"))
    if not 1024 <= port <= 65535:
        raise RuntimeError("PORT must be a valid non-privileged TCP port")
    public_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
    if public_host and ("/" in public_host or ":" in public_host):
        raise RuntimeError("Invalid public Render hostname")
    if not public_host:
        public_host = "localhost"
    public_scheme = "https" if public_host != "localhost" else "http"
    external_origin = f"{public_scheme}://{public_host}"
    frontend_origin = os.environ.get("FRONTEND_PUBLIC_URL", "").rstrip("/")
    if not frontend_origin:
        raise RuntimeError("Set FRONTEND_PUBLIC_URL to the Vercel https://...vercel.app origin")
    if not os.environ.get("DATABASE_URL"):
        raise RuntimeError("Set DATABASE_URL to the Neon PostgreSQL connection string")
    # Neon provides postgresql://?sslmode=require; SQLAlchemy asyncpg uses ssl=require.
    db_url = os.environ["DATABASE_URL"]
    if db_url.startswith("postgres://"):
        db_url = "postgresql://" + db_url[len("postgres://"):]
    if db_url.startswith("postgresql://"):
        db_url = "postgresql+asyncpg://" + db_url[len("postgresql://"):]
    if not db_url.startswith("postgresql+asyncpg://"):
        raise RuntimeError("Neon DATABASE_URL must use PostgreSQL")
    parts = urlsplit(db_url)
    params = [("ssl", value) if key == "sslmode" else (key, value)
              for key, value in parse_qsl(parts.query) if key != "channel_binding"]
    db_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params), parts.fragment))
    os.environ["DATABASE_URL"] = db_url

    for i in range(3):
        for key in (f"MPC_NODE{i}_TOKEN", f"MPC_FOUNDER_TOKEN_SECRET_{i}"):
            if len(os.environ.get(key, "")) < 32:
                raise RuntimeError(f"Set a random value of at least 32 characters for {key}")
    if len(os.environ.get("COORDINATOR_ADMIN_TOKEN", "")) < 32:
        raise RuntimeError("Set a random COORDINATOR_ADMIN_TOKEN of at least 32 characters")

    # Render terminates public HTTPS. The in-process ASGI routes and loopback
    # worker mesh use HTTP. Do not use this configuration on untrusted hosts.
    os.environ.update({
        "ENVIRONMENT": "demo", "DEBUG": "false",
        "DATABASE_AUTO_CREATE": "false", "MPC_REQUIRE_TLS": "false",
        "MPC_ENABLE_TLS": "false", "MPC_REQUIRE_CLIENT_CERT": "false",
        "FRONTEND_PUBLIC_URL": frontend_origin,
        "ALLOWED_ORIGINS": frontend_origin,
        "MPC_PARTY_ALLOWED_ORIGINS": frontend_origin,
        "MPC_PARTY_PUBLIC_URLS": ",".join(f"{external_origin}/party/{i}" for i in range(3)),
        **{f"MPC_NODE{i}_URL": f"http://127.0.0.1:{port}/party/{i}" for i in range(3)},
        **{f"MPC_PARTY_{i}_HOST": "127.0.0.1" for i in range(3)},
    })
    return port


async def ensure_admin():
    """One-time non-interactive bootstrap from private Render environment values."""
    username = os.environ.get("VEILBENCH_INITIAL_ADMIN_USERNAME", "").strip().lower()
    password = os.environ.get("VEILBENCH_INITIAL_ADMIN_PASSWORD", "")
    if not username or not password:
        raise RuntimeError("Set VEILBENCH_INITIAL_ADMIN_USERNAME and VEILBENCH_INITIAL_ADMIN_PASSWORD")
    from backend.api.accounts import Credentials
    from backend.models.account import Account
    from backend.security.accounts import hash_password
    from backend.services.database import database
    credentials = Credentials(username=username, password=password)
    await database.start()
    try:
        async for db in database.get_session():
            existing = await db.get(Account, credentials.username)
            if existing is None:
                db.add(Account(username=credentials.username, role="admin", password_hash=hash_password(credentials.password)))
                await db.commit()
                print("Initial administrator account provisioned", flush=True)
            elif existing.role != "admin":
                raise RuntimeError("Configured administrator username is already a participant")
    finally:
        await database.stop()


def main():
    port = configure()
    from alembic import command
    from alembic.config import Config
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    command.upgrade(Config(str(root / "alembic.ini")), "head")
    asyncio.run(ensure_admin())
    import uvicorn
    # Single worker is required: salaries are deliberately transient in-memory.
    uvicorn.run("backend.ops.free_host_app:app", host="0.0.0.0", port=port, workers=1, log_level="info")


if __name__ == "__main__":
    main()
