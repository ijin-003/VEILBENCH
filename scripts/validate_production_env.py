#!/usr/bin/env python3
"""Validate VEILBENCH production environment, certificate tree, and secret hygiene.

This script reports variable names and checks only. It never prints secret values.
Run it on the VPS after generating .env.production and securing certificates.
"""
from __future__ import annotations

import argparse
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SECRET_KEYS = [
    "COORDINATOR_ADMIN_TOKEN",
    "MPC_FOUNDER_TOKEN_SECRET_0",
    "MPC_FOUNDER_TOKEN_SECRET_1",
    "MPC_FOUNDER_TOKEN_SECRET_2",
    "MPC_NODE0_TOKEN",
    "MPC_NODE1_TOKEN",
    "MPC_NODE2_TOKEN",
]


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Invalid environment entry on line {line_number}")
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise ValueError(f"Invalid environment variable name on line {line_number}")
        if key in values:
            raise ValueError(f"Duplicate environment variable: {key}")
        values[key] = value
    return values


def validate_values(values: dict[str, str]) -> list[str]:
    errors: list[str] = []
    required = [
        *SECRET_KEYS,
        "ENVIRONMENT", "DEBUG", "DATABASE_AUTO_CREATE", "DATABASE_URL",
        "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB",
        "FRONTEND_PUBLIC_URL", "ALLOWED_ORIGINS", "MPC_PARTY_ALLOWED_ORIGINS",
        "MPC_PARTY_PUBLIC_URLS", "VEILBENCH_API_HOST",
        "VEILBENCH_PARTY0_HOST", "VEILBENCH_PARTY1_HOST", "VEILBENCH_PARTY2_HOST",
        "NEXT_PUBLIC_API_URL", "NEXT_PUBLIC_PARTY_0_URL",
        "NEXT_PUBLIC_PARTY_1_URL", "NEXT_PUBLIC_PARTY_2_URL",
        "MPC_REQUIRE_TLS", "MPC_REQUIRE_CLIENT_CERT", "MPC_PARTIES_COUNT", "MPC_THRESHOLD",
    ]
    missing = [name for name in required if not values.get(name)]
    if missing:
        errors.append("Missing required variables: " + ", ".join(missing))
        return errors

    if values["ENVIRONMENT"].lower() != "production":
        errors.append("ENVIRONMENT must be production")
    if values["DEBUG"].lower() != "false":
        errors.append("DEBUG must be false")
    if values["DATABASE_AUTO_CREATE"].lower() != "false":
        errors.append("DATABASE_AUTO_CREATE must be false")
    if values["MPC_REQUIRE_TLS"].lower() != "true":
        errors.append("MPC_REQUIRE_TLS must be true")
    if values["MPC_REQUIRE_CLIENT_CERT"].lower() != "true":
        errors.append("MPC_REQUIRE_CLIENT_CERT must be true")
    if values["MPC_PARTIES_COUNT"] != "3" or values["MPC_THRESHOLD"] != "1":
        errors.append("The academic deployment requires exactly three parties and threshold one")

    secrets = [values[name] for name in SECRET_KEYS]
    if any(len(secret) < 32 or secret.startswith("CHANGE_ME") for secret in secrets):
        errors.append("All seven application secrets must be unique random values of at least 32 characters")
    if len(set(secrets)) != len(secrets):
        errors.append("All seven application secrets must be distinct")

    frontend = values["FRONTEND_PUBLIC_URL"].rstrip("/")
    parsed_frontend = urlsplit(frontend)
    if parsed_frontend.scheme != "https" or not parsed_frontend.netloc or parsed_frontend.path:
        errors.append("FRONTEND_PUBLIC_URL must be an exact public HTTPS origin")
    if values["ALLOWED_ORIGINS"].split(",") != [frontend]:
        errors.append("ALLOWED_ORIGINS must contain only FRONTEND_PUBLIC_URL")
    if values["MPC_PARTY_ALLOWED_ORIGINS"].split(",") != [frontend]:
        errors.append("MPC_PARTY_ALLOWED_ORIGINS must contain only FRONTEND_PUBLIC_URL")

    party_urls = [item.strip().rstrip("/") for item in values["MPC_PARTY_PUBLIC_URLS"].split(",") if item.strip()]
    if len(party_urls) != 3 or len(set(party_urls)) != 3:
        errors.append("MPC_PARTY_PUBLIC_URLS must contain three distinct public party URLs")
    else:
        for index, url in enumerate(party_urls):
            parsed = urlsplit(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.path:
                errors.append(f"MPC_PARTY_PUBLIC_URLS entry {index} must be an HTTPS origin")
            expected = values[f"NEXT_PUBLIC_PARTY_{index}_URL"].rstrip("/")
            if url != expected:
                errors.append(f"NEXT_PUBLIC_PARTY_{index}_URL does not match MPC_PARTY_PUBLIC_URLS")
            if parsed.hostname != values[f"VEILBENCH_PARTY{index}_HOST"]:
                errors.append(f"VEILBENCH_PARTY{index}_HOST does not match its public party URL")

    api_url = urlsplit(values["NEXT_PUBLIC_API_URL"].rstrip("/"))
    if api_url.scheme != "https" or not api_url.hostname or api_url.path:
        errors.append("NEXT_PUBLIC_API_URL must be an HTTPS origin")
    elif api_url.hostname != values["VEILBENCH_API_HOST"]:
        errors.append("VEILBENCH_API_HOST does not match NEXT_PUBLIC_API_URL")

    database_url = urlsplit(values["DATABASE_URL"])
    if (
        database_url.scheme != "postgresql+asyncpg"
        or database_url.hostname != "veilbench-db"
        or unquote(database_url.username or "") != values["POSTGRES_USER"]
        or unquote(database_url.password or "") != values["POSTGRES_PASSWORD"]
        or database_url.path.lstrip("/") != values["POSTGRES_DB"]
    ):
        errors.append("DATABASE_URL must match the isolated PostgreSQL service credentials")

    for name, value in values.items():
        if name.startswith("NEXT_PUBLIC_") and any(secret in value for secret in secrets):
            errors.append(f"A private secret appears in browser-visible variable {name}")

    return errors


def _openssl(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=False)


def validate_certificates(cert_root: Path) -> list[str]:
    errors: list[str] = []
    ca_cert = cert_root / "ca" / "ca.crt"
    ca_key = cert_root / "ca" / "ca.key"
    edge_public_ca = cert_root / "edge" / "ca.crt"
    edge_cert = cert_root / "edge/edge.crt"
    edge_key = cert_root / "edge/edge.key"
    required = [ca_cert, ca_key, edge_public_ca, cert_root / "api/api.crt", cert_root / "api/api.key",
                cert_root / "coordinator/coordinator.crt", cert_root / "coordinator/coordinator.key",
                edge_cert, edge_key]
    for party_id in range(3):
        required.extend([
            cert_root / f"party_{party_id}/party_{party_id}.crt",
            cert_root / f"party_{party_id}/party_{party_id}.key",
            cert_root / f"party_{party_id}/control/control.crt",
            cert_root / f"party_{party_id}/control/control.key",
        ])
    missing = [str(path.relative_to(cert_root)) for path in required if not path.is_file()]
    if missing:
        errors.append("Missing certificate artifacts: " + ", ".join(missing))
        return errors

    if ca_cert.read_bytes() != edge_public_ca.read_bytes():
        errors.append("edge/ca.crt must be an exact copy of ca/ca.crt")

    private_keys = [path for path in required if path.suffix == ".key"]
    for key_path in private_keys:
        mode = stat.S_IMODE(key_path.stat().st_mode)
        if mode & 0o077:
            errors.append(f"Private key permissions are too broad: {key_path.relative_to(cert_root)}")
    if os.name == "posix":
        if ca_key.stat().st_uid != 0:
            errors.append("The CA private key must remain root-owned")
        edge_dir = edge_key.parent
        if edge_dir.stat().st_uid != 0 or stat.S_IMODE(edge_dir.stat().st_mode) & 0o022:
            errors.append("The edge certificate directory must be root-owned and not group/other-writable")
        for key_path in private_keys:
            expected_uid = 0 if key_path in {ca_key, edge_key} else 10001
            if key_path.stat().st_uid != expected_uid:
                owner = "root" if expected_uid == 0 else "UID 10001"
                errors.append(f"Private key must be owned by {owner}: {key_path.relative_to(cert_root)}")

    version = _openssl(["openssl", "version"])
    if version.returncode != 0:
        errors.append("OpenSSL CLI is required for production certificate validation")
        return errors

    ca_expiry = _openssl(["openssl", "x509", "-in", str(ca_cert), "-noout", "-checkend", "604800"])
    if ca_expiry.returncode != 0:
        errors.append("The internal CA certificate expires within seven days")
    ca_text = _openssl(["openssl", "x509", "-in", str(ca_cert), "-noout", "-text"])
    if ca_text.returncode != 0 or "CA:TRUE" not in ca_text.stdout or "Certificate Sign" not in ca_text.stdout:
        errors.append("The internal CA certificate must assert CA:TRUE and certificate-signing key usage")

    certificates = [path for path in required if path.suffix == ".crt" and path != ca_cert and path != edge_public_ca]
    for cert_path in certificates:
        verify = _openssl(["openssl", "verify", "-CAfile", str(ca_cert), str(cert_path)])
        if verify.returncode != 0:
            errors.append(f"Certificate chain validation failed: {cert_path.relative_to(cert_root)}")
            continue
        expiry = _openssl(["openssl", "x509", "-in", str(cert_path), "-noout", "-checkend", "604800"])
        if expiry.returncode != 0:
            errors.append(f"Certificate expires within seven days: {cert_path.relative_to(cert_root)}")

    key_pairs = [(ca_cert, ca_key), (cert_root / "api/api.crt", cert_root / "api/api.key"),
                 (cert_root / "coordinator/coordinator.crt", cert_root / "coordinator/coordinator.key"),
                 (edge_cert, edge_key)]
    for party_id in range(3):
        key_pairs.extend([
            (cert_root / f"party_{party_id}/party_{party_id}.crt", cert_root / f"party_{party_id}/party_{party_id}.key"),
            (cert_root / f"party_{party_id}/control/control.crt", cert_root / f"party_{party_id}/control/control.key"),
        ])
    for cert_path, key_path in key_pairs:
        cert_public = _openssl(["openssl", "x509", "-in", str(cert_path), "-pubkey", "-noout"])
        key_public = _openssl(["openssl", "pkey", "-in", str(key_path), "-pubout"])
        if cert_public.returncode != 0 or key_public.returncode != 0 or cert_public.stdout.strip() != key_public.stdout.strip():
            errors.append(f"Certificate and private key do not match: {cert_path.relative_to(cert_root)}")

    purpose_checks = [
        (cert_root / "api/api.crt", "sslserver"),
        *((cert_root / f"party_{i}/control/control.crt", "sslserver") for i in range(3)),
        *((cert_root / f"party_{i}/party_{i}.crt", "sslserver") for i in range(3)),
        *((cert_root / f"party_{i}/party_{i}.crt", "sslclient") for i in range(3)),
        (cert_root / "coordinator/coordinator.crt", "sslclient"),
        (edge_cert, "sslclient"),
    ]
    for cert_path, purpose in purpose_checks:
        purpose_result = _openssl([
            "openssl", "verify", "-purpose", purpose, "-CAfile", str(ca_cert), str(cert_path)
        ])
        if purpose_result.returncode != 0:
            errors.append(
                f"Certificate extended-key-usage is not valid for {purpose}: {cert_path.relative_to(cert_root)}"
            )

    name_checks = [
        (cert_root / "api/api.crt", "veilbench-backend"),
        *((cert_root / f"party_{i}/control/control.crt", f"veilbench-mpc-node{i}") for i in range(3)),
    ]
    for cert_path, hostname in name_checks:
        check = _openssl(["openssl", "x509", "-in", str(cert_path), "-noout", "-checkhost", hostname])
        if check.returncode != 0:
            errors.append(f"Certificate hostname validation failed for {hostname}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", default=str(ROOT / ".env.production"))
    parser.add_argument("--cert-root", default=str(ROOT / "infrastructure" / "certs"))
    args = parser.parse_args()
    env_path = Path(args.env_file).resolve()
    if not env_path.is_file():
        print(f"ERROR: environment file not found: {env_path}", file=sys.stderr)
        return 2
    if os.name == "posix" and stat.S_IMODE(env_path.stat().st_mode) & 0o077:
        print("ERROR: .env.production must not be accessible by group or other users", file=sys.stderr)
        return 2
    try:
        values = read_env(env_path)
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    errors = validate_values(values)
    errors.extend(validate_certificates(Path(args.cert_root).resolve()))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Production environment and certificate preflight passed. No secret values were displayed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
