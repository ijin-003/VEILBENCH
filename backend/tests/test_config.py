import os
from pathlib import Path

import pytest

from backend.config import Settings


def test_mpc_runtime_fails_closed_without_secrets(monkeypatch):
    secret_names = [
        "COORDINATOR_ADMIN_TOKEN",
        "MPC_FOUNDER_TOKEN_SECRET_0",
        "MPC_FOUNDER_TOKEN_SECRET_1",
        "MPC_FOUNDER_TOKEN_SECRET_2",
        "MPC_NODE0_TOKEN",
        "MPC_NODE1_TOKEN",
        "MPC_NODE2_TOKEN",
        "MPC_CA_CERT_PATH",
        "MPC_CLIENT_CERT_PATH",
        "MPC_CLIENT_KEY_PATH",
    ]

    for name in secret_names:
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None, MPC_REQUIRE_TLS=False)

    with pytest.raises(RuntimeError, match="COORDINATOR_ADMIN_TOKEN"):
        settings.validate_mpc_runtime()


def test_mpc_runtime_accepts_complete_explicit_configuration(tmp_path):
    ca = tmp_path / "ca.crt"
    cert = tmp_path / "coordinator.crt"
    key = tmp_path / "coordinator.key"
    for path in (ca, cert, key):
        path.write_text("test", encoding="utf-8")

    settings = Settings(
        COORDINATOR_ADMIN_TOKEN="admin",
        MPC_FOUNDER_TOKEN_SECRET_0="founder-secret-0",
        MPC_FOUNDER_TOKEN_SECRET_1="founder-secret-1",
        MPC_FOUNDER_TOKEN_SECRET_2="founder-secret-2",
        MPC_NODE0_TOKEN="p0",
        MPC_NODE1_TOKEN="p1",
        MPC_NODE2_TOKEN="p2",
        MPC_CA_CERT_PATH=str(ca),
        MPC_CLIENT_CERT_PATH=str(cert),
        MPC_CLIENT_KEY_PATH=str(key),
    )
    settings.validate_mpc_runtime()


def test_public_party_urls_must_be_distinct():
    settings = Settings(
        _env_file=None,
        MPC_REQUIRE_TLS=False,
        COORDINATOR_ADMIN_TOKEN="admin",
        MPC_FOUNDER_TOKEN_SECRET_0="founder-secret-0",
        MPC_FOUNDER_TOKEN_SECRET_1="founder-secret-1",
        MPC_FOUNDER_TOKEN_SECRET_2="founder-secret-2",
        MPC_NODE0_TOKEN="p0",
        MPC_NODE1_TOKEN="p1",
        MPC_NODE2_TOKEN="p2",
        MPC_PARTY_PUBLIC_URLS=["https://same.example", "https://same.example", "https://third.example"],
    )

    with pytest.raises(RuntimeError, match="three distinct party endpoints"):
        settings.validate_mpc_runtime()


def test_production_requires_public_https_origins_and_tls(tmp_path):
    ca = tmp_path / "ca.crt"
    cert = tmp_path / "coordinator.crt"
    key = tmp_path / "coordinator.key"
    for path in (ca, cert, key):
        path.write_text("test", encoding="utf-8")

    settings = Settings(
        _env_file=None,
        ENVIRONMENT="production",
        MPC_REQUIRE_TLS=False,
        FRONTEND_PUBLIC_URL="http://demo.example.test",
        ALLOWED_ORIGINS=["http://different.example.test"],
        MPC_PARTY_PUBLIC_URLS=[
            "http://party0.example.test",
            "http://party1.example.test",
            "http://party2.example.test",
        ],
        COORDINATOR_ADMIN_TOKEN="admin",
        MPC_FOUNDER_TOKEN_SECRET_0="founder-secret-0",
        MPC_FOUNDER_TOKEN_SECRET_1="founder-secret-1",
        MPC_FOUNDER_TOKEN_SECRET_2="founder-secret-2",
        MPC_NODE0_TOKEN="p0",
        MPC_NODE1_TOKEN="p1",
        MPC_NODE2_TOKEN="p2",
        MPC_CA_CERT_PATH=str(ca),
        MPC_CLIENT_CERT_PATH=str(cert),
        MPC_CLIENT_KEY_PATH=str(key),
    )

    with pytest.raises(RuntimeError) as error:
        settings.validate_mpc_runtime()
    message = str(error.value)
    assert "HTTPS" in message
    assert "ALLOWED_ORIGINS" in message
    assert "MPC_REQUIRE_TLS" in message


def test_complete_production_browser_endpoints_are_accepted(tmp_path):
    ca = tmp_path / "ca.crt"
    cert = tmp_path / "coordinator.crt"
    key = tmp_path / "coordinator.key"
    for path in (ca, cert, key):
        path.write_text("test", encoding="utf-8")

    settings = Settings(
        _env_file=None,
        ENVIRONMENT="production",
        FRONTEND_PUBLIC_URL="https://veilbench-demo.vercel.app",
        ALLOWED_ORIGINS=["https://veilbench-demo.vercel.app"],
        MPC_PARTY_PUBLIC_URLS=[
            "https://party0.example.test",
            "https://party1.example.test",
            "https://party2.example.test",
        ],
        COORDINATOR_ADMIN_TOKEN="admin",
        MPC_FOUNDER_TOKEN_SECRET_0="founder-secret-0",
        MPC_FOUNDER_TOKEN_SECRET_1="founder-secret-1",
        MPC_FOUNDER_TOKEN_SECRET_2="founder-secret-2",
        MPC_NODE0_TOKEN="p0",
        MPC_NODE1_TOKEN="p1",
        MPC_NODE2_TOKEN="p2",
        MPC_CA_CERT_PATH=str(ca),
        MPC_CLIENT_CERT_PATH=str(cert),
        MPC_CLIENT_KEY_PATH=str(key),
    )

    settings.validate_mpc_runtime()


def _production_settings(tmp_path, **overrides):
    files = []
    for name in ("ca.crt", "coordinator.crt", "coordinator.key"):
        path = tmp_path / name
        path.write_text("test", encoding="utf-8")
        if name == "coordinator.key":
            path.chmod(0o600)
        files.append(str(path))
    values = {
        "_env_file": None,
        "ENVIRONMENT": "production",
        "DEBUG": False,
        "DATABASE_AUTO_CREATE": False,
        "DATABASE_URL": "postgresql+asyncpg://veilbench:password@db:5432/veilbench",
        "FRONTEND_PUBLIC_URL": "https://veilbench-demo.vercel.app",
        "ALLOWED_ORIGINS": ["https://veilbench-demo.vercel.app"],
        "MPC_PARTY_PUBLIC_URLS": [
            "https://party0.example.test",
            "https://party1.example.test",
            "https://party2.example.test",
        ],
        "COORDINATOR_ADMIN_TOKEN": "a" * 48,
        "MPC_FOUNDER_TOKEN_SECRET_0": "b" * 48,
        "MPC_FOUNDER_TOKEN_SECRET_1": "c" * 48,
        "MPC_FOUNDER_TOKEN_SECRET_2": "d" * 48,
        "MPC_NODE0_TOKEN": "e" * 48,
        "MPC_NODE1_TOKEN": "f" * 48,
        "MPC_NODE2_TOKEN": "g" * 48,
        "MPC_CA_CERT_PATH": files[0],
        "MPC_CLIENT_CERT_PATH": files[1],
        "MPC_CLIENT_KEY_PATH": files[2],
        "MPC_REQUIRE_TLS": True,
    }
    values.update(overrides)
    return Settings(**values)


def test_production_configuration_accepts_secure_settings(tmp_path):
    settings = _production_settings(tmp_path)
    settings.validate_production_configuration()


def test_production_configuration_rejects_auto_create_and_short_secrets(tmp_path):
    settings = _production_settings(
        tmp_path,
        DATABASE_AUTO_CREATE=True,
        COORDINATOR_ADMIN_TOKEN="short",
    )
    with pytest.raises(RuntimeError) as error:
        settings.validate_production_configuration()
    assert "DATABASE_AUTO_CREATE" in str(error.value)
    assert "at least 32 characters" in str(error.value)


def test_production_configuration_rejects_non_postgresql_database(tmp_path):
    settings = _production_settings(tmp_path, DATABASE_URL="sqlite:///not-for-production.db")
    with pytest.raises(RuntimeError, match=r"postgresql\+asyncpg"):
        settings.validate_production_configuration()


def test_production_configuration_rejects_missing_certificate(tmp_path):
    settings = _production_settings(tmp_path, MPC_CLIENT_KEY_PATH=str(tmp_path / "missing.key"))
    with pytest.raises(RuntimeError, match="MPC_CLIENT_KEY_PATH"):
        settings.validate_production_configuration()


@pytest.mark.skipif(
    os.name != "posix",
    reason="POSIX chmod permission bits are enforced on the Linux production host, not Windows development hosts",
)
def test_production_configuration_rejects_world_readable_client_key(tmp_path):
    settings = _production_settings(tmp_path)
    key_path = Path(settings.MPC_CLIENT_KEY_PATH)
    key_path.chmod(0o644)
    with pytest.raises(RuntimeError, match="group or other users"):
        settings.validate_production_configuration()


def test_production_configuration_rejects_localhost_party_origin(tmp_path):
    settings = _production_settings(
        tmp_path,
        MPC_PARTY_PUBLIC_URLS=[
            "https://localhost:8100",
            "https://party1.example.test",
            "https://party2.example.test",
        ],
    )
    with pytest.raises(RuntimeError, match="localhost"):
        settings.validate_production_configuration()
