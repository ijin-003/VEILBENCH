import pytest

from backend.config import Settings


def test_mpc_runtime_fails_closed_without_secrets():
    settings = Settings(MPC_REQUIRE_TLS=False)
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
