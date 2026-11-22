#!/usr/bin/env python3
"""
Generate TLS certificates for VEILBENCH MPC party nodes.

Usage:
    python scripts/generate_certs.py [--output-dir infrastructure/certs]

Generates a local CA, MPyC peer certificates, HTTPS party-control
certificates, and backend/coordinator TLS certificates under
``infrastructure/certs``. The generated material is for local academic use.

TRUST MODEL NOTE:
    In this academic demo, all certificates are generated on a single machine.
    In a real multi-organization deployment, each organization would:
    1. Generate its own private key locally.
    2. Create a CSR (Certificate Signing Request).
    3. Submit the CSR to a shared CA or external PKI.
    4. Receive its signed certificate.
    The private key never leaves the organization's control.
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from backend.mpc.certificates import check_openssl_available, generate_certificates  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="Generate TLS certificates for VEILBENCH MPC nodes"
    )
    parser.add_argument(
        "--output-dir",
        default=str(project_root / "infrastructure" / "certs"),
        help="Directory for generated certificates (default: infrastructure/certs/)",
    )
    parser.add_argument(
        "--parties",
        type=int,
        default=3,
        help="Number of party certificates to generate (default: 3)",
    )
    parser.add_argument(
        "--validity-days",
        type=int,
        default=365,
        help="Certificate validity in days (default: 365)",
    )
    args = parser.parse_args()

    if not check_openssl_available():
        print("ERROR: OpenSSL CLI is not available on this system.", file=sys.stderr)
        print("Install OpenSSL and ensure it is on your PATH.", file=sys.stderr)
        sys.exit(1)

    print(f"Generating certificates for {args.parties} parties...")
    print(f"Output directory: {args.output_dir}")
    print(f"Validity: {args.validity_days} days")
    print()

    result = generate_certificates(
        output_dir=args.output_dir,
        parties_count=args.parties,
        validity_days=args.validity_days,
    )

    print("Certificate generation complete!")
    print()
    for party_id, paths in result["parties"].items():
        print(f"  Party {party_id}:")
        print(f"    MPyC cert:    {paths['mpyc']['cert']}")
        print(f"    Control cert: {paths['control']['cert']}")
    print(f"  API cert:         {result['api']['cert']}")
    print(f"  Coordinator cert: {result['coordinator']['cert']}")
    print(f"  Edge client cert: {result['edge']['cert']}")
    print()
    print("SECURITY REMINDERS:")
    print("  - ca/ca.key is the CA private key. NEVER distribute it.")
    print("  - Each party key, coordinator.key, and edge.key must stay with its owner ONLY.")
    print("  - Self-signed certs are for development/academic use only.")
    print("  - Add infrastructure/certs/ to .gitignore (already done).")


if __name__ == "__main__":
    main()
