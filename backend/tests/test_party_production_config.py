import pytest

from backend.mpc import party_service


def _configure_party_for_production(monkeypatch, tmp_path):
    cert_root = tmp_path / "certs"
    config_root = tmp_path / "config"
    state_root = tmp_path / "state"
    cert_root.mkdir()
    config_root.mkdir()
    state_root.mkdir()

    paths = [
        cert_root / "ca.crt",
        cert_root / "control.crt",
        cert_root / "control.key",
        config_root / "mpyc_ca.crt",
        config_root / "party_0.crt",
        config_root / "party_0.key",
    ]
    for path in paths:
        path.write_text("test", encoding="utf-8")
    for path in (cert_root / "control.key", config_root / "party_0.key"):
        path.chmod(0o600)

    monkeypatch.setattr(party_service, "PARTY_ID", 0)
    monkeypatch.setattr(party_service, "PARTIES_COUNT", 3)
    monkeypatch.setattr(party_service, "CONTROL_TOKEN", "c" * 48)
    monkeypatch.setattr(party_service, "FOUNDER_TOKEN_SECRET", "f" * 48)
    monkeypatch.setattr(party_service, "MPC_ENABLE_TLS", True)
    monkeypatch.setattr(party_service, "MPC_REQUIRE_CLIENT_CERT", True)
    monkeypatch.setattr(party_service, "ALLOWED_ORIGINS", ["https://demo.vercel.app"])
    monkeypatch.setattr(party_service, "STATE_DB_PATH", str(state_root / "state.sqlite3"))
    monkeypatch.setattr(party_service, "_production_certificate_paths", lambda party_id: paths)
    return paths


def test_production_party_configuration_accepts_secure_settings(monkeypatch, tmp_path):
    paths = _configure_party_for_production(monkeypatch, tmp_path)
    monkeypatch.setattr(party_service, "_production_certificate_paths", lambda party_id: paths)
    party_service.validate_production_party_configuration()


def test_production_party_configuration_rejects_insecure_origins(monkeypatch, tmp_path):
    _configure_party_for_production(monkeypatch, tmp_path)
    monkeypatch.setattr(party_service, "ALLOWED_ORIGINS", ["*"])
    with pytest.raises(RuntimeError, match="exact HTTPS origins"):
        party_service.validate_production_party_configuration()


def test_production_party_configuration_rejects_short_credentials(monkeypatch, tmp_path):
    _configure_party_for_production(monkeypatch, tmp_path)
    monkeypatch.setattr(party_service, "CONTROL_TOKEN", "short")
    with pytest.raises(RuntimeError, match="at least 32 characters"):
        party_service.validate_production_party_configuration()


def test_production_party_configuration_rejects_relative_state_path(monkeypatch, tmp_path):
    _configure_party_for_production(monkeypatch, tmp_path)
    monkeypatch.setattr(party_service, "STATE_DB_PATH", ".state/party.sqlite3")
    with pytest.raises(RuntimeError, match="must be absolute"):
        party_service.validate_production_party_configuration()


def test_production_party_configuration_requires_mutual_tls_client_cert(monkeypatch, tmp_path):
    _configure_party_for_production(monkeypatch, tmp_path)
    monkeypatch.setattr(party_service, "MPC_REQUIRE_CLIENT_CERT", False)
    with pytest.raises(RuntimeError, match="MPC_REQUIRE_CLIENT_CERT"):
        party_service.validate_production_party_configuration()
