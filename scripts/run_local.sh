#!/usr/bin/env bash
# VEILBENCH needs three party processes and TLS for any private-input workflow.
# This script intentionally does not start the old insecure single-process
# HTTP development topology.

set -euo pipefail
echo "VEILBENCH secure local run"
echo "Use docs/PHASE_0_TO_4_DELIVERY.md to generate certificates and run Docker Compose."
exit 1
