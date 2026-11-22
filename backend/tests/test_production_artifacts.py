import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_production_compose_publishes_only_the_edge_proxy():
    compose = (ROOT / "docker-compose.production.yml").read_text(encoding="utf-8")
    assert compose.count("    ports:") == 1
    assert '"80:80"' in compose
    assert '"443:443"' in compose
    assert "5432:" not in compose
    assert '"8000:8000"' not in compose
    assert '"8100:8100"' not in compose
    assert '"8101:8100"' not in compose
    assert '"8102:8100"' not in compose
    assert "internal: true" in compose
    assert "DATABASE_AUTO_CREATE: \"false\"" in compose
    assert "validate_production_configuration()" in compose
    assert "alembic upgrade head" in compose


def test_public_party_proxy_exposes_only_founder_input_and_health():
    caddy = (ROOT / "infrastructure/caddy/Caddyfile").read_text(encoding="utf-8")
    assert caddy.count("path_regexp founder_input") == 3
    assert caddy.count("path /health\n") == 3
    active_config = "\n".join(
        line for line in caddy.splitlines() if not line.lstrip().startswith("#")
    )
    for forbidden in ("/compute", "/result", "/shutdown", "/status"):
        assert forbidden not in active_config
    assert "tls_trust_pool file /etc/caddy/certs/ca.crt" in caddy
    assert "tls_insecure_skip_verify" not in caddy


def test_alembic_initial_migration_matches_metadata_only_model():
    migration = ROOT / "backend/migrations/versions/0001_initial_session_metadata.py"
    assert migration.is_file()
    source = migration.read_text(encoding="utf-8").lower()
    assert '"benchmark_sessions"' in source
    assert '"aggregate_sum"' in source
    assert '"average_salary"' in source
    assert "salary" not in source.replace('"aggregate_sum"', "").replace('"average_salary"', "")
    assert "create_index" in source


def test_production_environment_generator_creates_distinct_secrets(tmp_path):
    output = tmp_path / ".env.production"
    script = ROOT / "scripts/generate_production_env.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--vps-ip",
            "8.8.8.8",
            "--frontend-origin",
            "https://veilbench-demo.vercel.app",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Created" in result.stdout
    values = {}
    for line in output.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value
    secrets = [
        values["COORDINATOR_ADMIN_TOKEN"],
        values["MPC_FOUNDER_TOKEN_SECRET_0"],
        values["MPC_FOUNDER_TOKEN_SECRET_1"],
        values["MPC_FOUNDER_TOKEN_SECRET_2"],
        values["MPC_NODE0_TOKEN"],
        values["MPC_NODE1_TOKEN"],
        values["MPC_NODE2_TOKEN"],
    ]
    assert len(set(secrets)) == 7
    assert all(len(secret) >= 32 for secret in secrets)
    assert values["DATABASE_AUTO_CREATE"] == "false"
    assert values["NEXT_PUBLIC_API_URL"] == "https://api.8.8.8.8.sslip.io"
    assert values["NEXT_PUBLIC_PARTY_2_URL"] == "https://party2.8.8.8.8.sslip.io"
    assert values["FRONTEND_PUBLIC_URL"] == "https://veilbench-demo.vercel.app"
    if sys.platform != "win32":
        assert output.stat().st_mode & 0o777 == 0o600


def test_production_env_generator_refuses_overwrite_without_force(tmp_path):
    output = tmp_path / ".env.production"
    output.write_text("KEEP_ME=true\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/generate_production_env.py"),
            "--vps-ip",
            "8.8.8.8",
            "--frontend-origin",
            "https://veilbench-demo.vercel.app",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert output.read_text(encoding="utf-8") == "KEEP_ME=true\n"


def test_production_compose_scopes_environment_secrets_per_service():
    compose = (ROOT / "docker-compose.production.yml").read_text(encoding="utf-8")
    assert "    env_file:" not in compose

    def service_block(name, next_name):
        start = compose.index(f"  {name}:")
        end = compose.index(f"  {next_name}:", start)
        return compose[start:end]

    db = service_block("veilbench-db", "veilbench-mpc-node0")
    party0 = service_block("veilbench-mpc-node0", "veilbench-mpc-node1")
    party1 = service_block("veilbench-mpc-node1", "veilbench-mpc-node2")
    party2 = service_block("veilbench-mpc-node2", "veilbench-backend")
    backend = service_block("veilbench-backend", "veilbench-edge")
    edge = compose[compose.index("  veilbench-edge:"):]
    assert "MPC_" not in db
    assert "COORDINATOR_ADMIN_TOKEN" not in db
    assert "MPC_FOUNDER_TOKEN_SECRET_0" in party0
    assert "MPC_FOUNDER_TOKEN_SECRET_1" not in party0
    assert "MPC_FOUNDER_TOKEN_SECRET_2" not in party0
    assert "MPC_NODE0_TOKEN" in party0
    assert "MPC_NODE1_TOKEN" not in party0
    assert "MPC_NODE2_TOKEN" not in party0
    assert "MPC_FOUNDER_TOKEN_SECRET_1" in party1
    assert "MPC_FOUNDER_TOKEN_SECRET_0" not in party1
    assert "MPC_FOUNDER_TOKEN_SECRET_2" not in party1
    assert "MPC_FOUNDER_TOKEN_SECRET_2" in party2
    assert "MPC_FOUNDER_TOKEN_SECRET_0" not in party2
    assert "MPC_FOUNDER_TOKEN_SECRET_1" not in party2
    assert all(f"MPC_FOUNDER_TOKEN_SECRET_{i}" in backend for i in range(3))
    assert "COORDINATOR_ADMIN_TOKEN" not in party0 + party1 + party2 + edge
    assert "POSTGRES_PASSWORD" not in backend + edge
    assert "MPC_NODE0_TOKEN" not in edge
    assert "MPC_FOUNDER_TOKEN_SECRET_0" not in edge



def test_container_healthchecks_present_authorized_client_certificates():
    backend = (ROOT / "infrastructure/Dockerfile.backend").read_text(encoding="utf-8")
    party = (ROOT / "infrastructure/Dockerfile.mpc-node").read_text(encoding="utf-8")
    assert "load_cert_chain('/app/certs/coordinator/coordinator.crt','/app/certs/coordinator/coordinator.key')" in backend
    assert "load_cert_chain(f'/app/.config/party_{p}.crt',f'/app/.config/party_{p}.key')" in party
    assert "curl --fail" not in backend


def test_production_edge_image_is_pinned_and_runs_with_expected_file_identity():
    compose = (ROOT / "docker-compose.production.yml").read_text(encoding="utf-8")
    edge = compose[compose.index("  veilbench-edge:"):compose.index("\nnetworks:")]
    assert "image: caddy:2.11.9-alpine" in edge
    assert 'user: "0:0"' in edge
    assert "NET_BIND_SERVICE" in edge
