import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_env_validator():
    path = ROOT / "scripts" / "validate_production_env.py"
    spec = importlib.util.spec_from_file_location("veilbench_validate_production_env", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _generated_env(tmp_path: Path) -> dict[str, str]:
    output = tmp_path / ".env.production"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "generate_production_env.py"),
            "--vps-ip", "8.8.8.8",
            "--frontend-origin", "https://veilbench-demo.vercel.app",
            "--output", str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return _load_env_validator().read_env(output)


def test_production_env_validator_accepts_generated_configuration(tmp_path):
    validator = _load_env_validator()
    values = _generated_env(tmp_path)
    assert validator.validate_values(values) == []


def test_production_env_validator_rejects_mismatched_frontend_origin(tmp_path):
    validator = _load_env_validator()
    values = _generated_env(tmp_path)
    values["MPC_PARTY_ALLOWED_ORIGINS"] = "https://attacker.example"
    errors = validator.validate_values(values)
    assert any("MPC_PARTY_ALLOWED_ORIGINS" in error for error in errors)


def test_production_env_validator_rejects_reused_secrets(tmp_path):
    validator = _load_env_validator()
    values = _generated_env(tmp_path)
    values["MPC_NODE0_TOKEN"] = values["MPC_NODE1_TOKEN"]
    errors = validator.validate_values(values)
    assert any("distinct" in error for error in errors)


def test_production_env_validator_rejects_database_url_mismatch(tmp_path):
    validator = _load_env_validator()
    values = _generated_env(tmp_path)
    values["POSTGRES_PASSWORD"] = "different-password"
    errors = validator.validate_values(values)
    assert any("DATABASE_URL" in error for error in errors)


def test_backend_image_creates_all_certificate_mount_directories():
    dockerfile = (ROOT / "infrastructure" / "Dockerfile.backend").read_text(encoding="utf-8")
    assert "/app/certs/ca /app/certs/api /app/certs/coordinator" in dockerfile


def test_caddy_receives_dedicated_edge_identity_and_required_bind_capability():
    compose = (ROOT / "docker-compose.production.yml").read_text(encoding="utf-8")
    edge = compose[compose.index("  veilbench-edge:"):]
    assert "./infrastructure/certs/edge:/etc/caddy/certs:ro" in edge
    assert "./infrastructure/certs/public-ca:/etc/caddy/certs:ro" not in edge
    assert "cap_drop:" in edge and "- ALL" in edge
    assert "cap_add:" in edge and "- NET_BIND_SERVICE" in edge
    assert "./infrastructure/certs/ca:/etc/caddy/certs" not in edge
    assert "ca.key" not in edge


def test_certificate_hardening_creates_public_ca_copy_without_mounting_ca_key():
    script = (ROOT / "scripts" / "secure_production_certs.sh").read_text(encoding="utf-8")
    assert 'install -o root -g root -m 644 "$CA_CERT" "$EDGE_DIR/ca.crt"' in script
    assert 'chown root:root "$CA_KEY"' in script
    assert 'chown root:root "$EDGE_KEY"' in script
    assert 'chmod 600 "$EDGE_KEY"' in script
    assert 'chmod 600 "$CA_KEY"' in script


def test_vps_deploy_script_validates_before_up_and_never_deletes_volumes():
    script = (ROOT / "scripts" / "deploy_vps.sh").read_text(encoding="utf-8")
    assert "validate_production_env.py" in script
    assert "config --quiet" in script
    assert "--entrypoint caddy" in script
    assert "scripts/build_production_images.sh" in script
    assert "up -d --no-build --remove-orphans" in script
    assert "up -d --build" not in script
    assert "down -v" not in script


def test_public_smoke_test_checks_auth_cors_and_hidden_control_routes():
    script = (ROOT / "scripts" / "smoke_test_public.py").read_text(encoding="utf-8")
    assert "access-control-allow-origin" in script
    assert "input_status != 401" in script
    assert "control_status != 404" in script
    assert "compute_status != 404" in script
    assert "salary" in script


def test_restore_script_requires_explicit_confirmation():
    script = (ROOT / "scripts" / "restore_postgres.sh").read_text(encoding="utf-8")
    assert 'CONFIRM_RESTORE:-' in script
    assert '!= "YES"' in script
    assert "pg_restore --clean --if-exists" in script


def test_deployment_docs_distinguish_live_deployment_from_preparation():
    docs = (ROOT / "docs" / "PHASE_4_DEPLOYMENT.md").read_text(encoding="utf-8")
    assert "does not claim that a live cloud deployment has already happened" in docs
    assert "three-founder" in docs
    assert "smoke_test_public.py" in docs
    assert "Never use `docker compose down -v`" in docs



def test_production_internal_https_requires_client_certificates():
    compose = (ROOT / "docker-compose.production.yml").read_text(encoding="utf-8")
    assert "--ssl-cert-reqs 2" in compose
    assert compose.count('      - "2"') == 3
    for party_id in range(3):
        start = compose.index(f"  veilbench-mpc-node{party_id}:")
        next_marker = (
            f"  veilbench-mpc-node{party_id + 1}:" if party_id < 2 else "  veilbench-backend:"
        )
        end = compose.index(next_marker, start)
        party_block = compose[start:end]
        assert party_block.count("    command:") == 1
        assert party_block.count("--ssl-cert-reqs") == 1
        assert '      - "2"' in party_block
    assert compose.count("--ssl-cert-reqs") == 4
    assert "MPC_REQUIRE_CLIENT_CERT: ${MPC_REQUIRE_CLIENT_CERT:?set client certificate enforcement}" in compose


def test_caddy_presents_dedicated_edge_client_certificate_to_every_internal_upstream():
    caddy = (ROOT / "infrastructure/caddy/Caddyfile").read_text(encoding="utf-8")
    assert caddy.count("tls_client_auth /etc/caddy/certs/edge.crt /etc/caddy/certs/edge.key") == 8
    compose = (ROOT / "docker-compose.production.yml").read_text(encoding="utf-8")
    edge = compose[compose.index("  veilbench-edge:"):]
    assert "./infrastructure/certs/edge:/etc/caddy/certs:ro" in edge
    assert "coordinator/coordinator.key" not in edge


def test_database_network_is_not_shared_with_public_edge():
    compose = (ROOT / "docker-compose.production.yml").read_text(encoding="utf-8")

    def block(name, next_name):
        start = compose.index(f"  {name}:")
        end = compose.index(f"  {next_name}:", start)
        return compose[start:end]

    database = block("veilbench-db", "veilbench-mpc-node0")
    backend = block("veilbench-backend", "veilbench-edge")
    edge_start = compose.index("  veilbench-edge:")
    edge_end = compose.index("\nnetworks:", edge_start)
    edge = compose[edge_start:edge_end]
    assert "- database-internal" in database
    assert "- database-internal" in backend
    assert "- backend-edge" in backend
    assert "- backend-edge" in edge
    assert "database-internal" not in edge
    assert "app-internal" not in compose


def test_deployment_runs_internal_mtls_smoke_test_before_public_smoke_test():
    deploy = (ROOT / "scripts/deploy_vps.sh").read_text(encoding="utf-8")
    internal = 'python -m backend.ops.smoke_test_internal_mtls'
    assert internal in deploy
    assert deploy.index(internal) < deploy.index('python3 scripts/smoke_test_public.py')
    smoke = ROOT / "backend/ops/smoke_test_internal_mtls.py"
    assert smoke.is_file()
    source = smoke.read_text(encoding="utf-8")
    assert "load_cert_chain" in source
    assert "accepted a TLS client without a certificate" in source
    assert "_check_backend(authenticated, anonymous)" in source


def test_production_certificate_hardening_scopes_edge_key_to_caddy():
    script = (ROOT / "scripts/secure_production_certs.sh").read_text(encoding="utf-8")
    validator = (ROOT / "scripts/validate_production_env.py").read_text(encoding="utf-8")
    assert 'EDGE_KEY="$EDGE_DIR/edge.key"' in script
    assert 'chown root:root "$EDGE_KEY"' in script
    assert 'chmod 600 "$EDGE_KEY"' in script
    assert 'cert_root / "edge/edge.crt"' in validator
    assert 'cert_root / "edge/edge.key"' in validator
    assert 'cert_root / "edge" / "ca.crt"' in validator
    assert '"sslclient"' in validator


def test_production_env_validator_rejects_disabled_client_certificate_enforcement(tmp_path):
    validator = _load_env_validator()
    values = _generated_env(tmp_path)
    values["MPC_REQUIRE_CLIENT_CERT"] = "false"
    errors = validator.validate_values(values)
    assert any("MPC_REQUIRE_CLIENT_CERT" in error for error in errors)



def test_phase5_env_migration_adds_flag_without_rotating_existing_secrets(tmp_path):
    env_file = tmp_path / ".env.production"
    env_file.write_text("COORDINATOR_ADMIN_TOKEN=keep-this-secret\nPOSTGRES_PASSWORD=keep-this-password\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/migrate_phase5_env.py"), str(env_file)],
        capture_output=True, text=True, check=True,
    )
    updated = env_file.read_text(encoding="utf-8")
    assert "MPC_REQUIRE_CLIENT_CERT=true" in updated
    assert "COORDINATOR_ADMIN_TOKEN=keep-this-secret" in updated
    assert "POSTGRES_PASSWORD=keep-this-password" in updated
    assert "without rotating any secrets" in result.stdout


def test_phase5_env_migration_is_idempotent_and_enables_existing_false_flag(tmp_path):
    env_file = tmp_path / ".env.production"
    env_file.write_text("MPC_REQUIRE_CLIENT_CERT=false\n", encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "scripts/migrate_phase5_env.py"), str(env_file)], check=True)
    assert env_file.read_text(encoding="utf-8").count("MPC_REQUIRE_CLIENT_CERT=") == 1
    assert "MPC_REQUIRE_CLIENT_CERT=true" in env_file.read_text(encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/migrate_phase5_env.py"), str(env_file)],
        capture_output=True, text=True, check=True,
    )
    assert "already enabled" in result.stdout
