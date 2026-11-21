"""Development certificate generation for the VEILBENCH TLS topology.

MPyC has fixed peer-hostname validation. Its party certificates therefore use
``CN=MPyC party <id>`` without an unrelated SAN, while HTTPS control-plane
certificates use the Docker service hostname and localhost SANs.
"""

import subprocess
from pathlib import Path

CERT_VALIDITY_DAYS = 365
KEY_SIZE = 2048


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True)


def _create_key(path: Path) -> None:
    if not path.exists():
        _run(["openssl", "genrsa", "-out", str(path), str(KEY_SIZE)])


def _sign_certificate(
    *,
    base: Path,
    name: str,
    subject: str,
    extension_lines: list[str],
    ca_key: Path,
    ca_cert: Path,
    validity_days: int,
) -> dict[str, str]:
    target = base / name
    target.mkdir(parents=True, exist_ok=True)
    key = target / f"{name}.key"
    csr = target / f"{name}.csr"
    cert = target / f"{name}.crt"
    extension = target / f"{name}.ext"
    _create_key(key)
    if not csr.exists():
        _run(["openssl", "req", "-new", "-key", str(key), "-out", str(csr), "-subj", subject])
    if not cert.exists():
        extension.write_text("\n".join(extension_lines) + "\n", encoding="utf-8")
        _run(
            [
                "openssl", "x509", "-req", "-in", str(csr), "-CA", str(ca_cert),
                "-CAkey", str(ca_key), "-CAcreateserial", "-out", str(cert),
                "-days", str(validity_days), "-extfile", str(extension),
            ]
        )
    return {"key": str(key), "cert": str(cert), "ca_cert": str(ca_cert)}


def generate_certificates(
    output_dir: str,
    parties_count: int = 3,
    validity_days: int = CERT_VALIDITY_DAYS,
) -> dict[str, object]:
    """Generate a local CA plus separate MPyC and HTTPS certificate material."""
    if parties_count != 3:
        raise ValueError("VEILBENCH requires exactly three MPC party certificates")
    base = Path(output_dir)
    ca_dir = base / "ca"
    ca_dir.mkdir(parents=True, exist_ok=True)
    ca_key = ca_dir / "ca.key"
    ca_cert = ca_dir / "ca.crt"
    _create_key(ca_key)
    if not ca_cert.exists():
        _run(
            [
                "openssl", "req", "-new", "-x509", "-key", str(ca_key), "-out", str(ca_cert),
                "-days", str(validity_days), "-subj", "/CN=VEILBENCH Development CA/O=VEILBENCH",
            ]
        )

    parties: dict[int, dict[str, dict[str, str]]] = {}
    for party_id in range(parties_count):
        party_root = base / f"party_{party_id}"
        # MPyC validates peers with server_hostname='MPyC party <id>'. Do not
        # add a node-name SAN here because Python gives SAN precedence over CN.
        mpyc = _sign_certificate(
            base=base,
            name=f"party_{party_id}",
            subject=f"/CN=MPyC party {party_id}/O=VEILBENCH/OU=MPC",
            extension_lines=["basicConstraints=CA:FALSE", "extendedKeyUsage=serverAuth,clientAuth"],
            ca_key=ca_key,
            ca_cert=ca_cert,
            validity_days=validity_days,
        )
        control = _sign_certificate(
            base=party_root,
            name="control",
            subject=f"/CN=veilbench-mpc-node{party_id}/O=VEILBENCH/OU=Control",
            extension_lines=[
                f"subjectAltName=DNS:veilbench-mpc-node{party_id},DNS:localhost,IP:127.0.0.1",
                "basicConstraints=CA:FALSE",
                "extendedKeyUsage=serverAuth",
            ],
            ca_key=ca_key,
            ca_cert=ca_cert,
            validity_days=validity_days,
        )
        parties[party_id] = {"mpyc": mpyc, "control": control}

    api = _sign_certificate(
        base=base,
        name="api",
        subject="/CN=veilbench-backend/O=VEILBENCH/OU=API",
        extension_lines=[
            "subjectAltName=DNS:veilbench-backend,DNS:localhost,IP:127.0.0.1",
            "basicConstraints=CA:FALSE",
            "extendedKeyUsage=serverAuth",
        ],
        ca_key=ca_key,
        ca_cert=ca_cert,
        validity_days=validity_days,
    )
    coordinator = _sign_certificate(
        base=base,
        name="coordinator",
        subject="/CN=veilbench-coordinator/O=VEILBENCH/OU=Control",
        extension_lines=["basicConstraints=CA:FALSE", "extendedKeyUsage=clientAuth"],
        ca_key=ca_key,
        ca_cert=ca_cert,
        validity_days=validity_days,
    )
    return {"parties": parties, "api": api, "coordinator": coordinator}


def check_openssl_available() -> bool:
    try:
        return subprocess.run(["openssl", "version"], capture_output=True, check=False).returncode == 0
    except FileNotFoundError:
        return False
