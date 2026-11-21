# VEILBENCH needs three party processes and TLS for any private-input workflow.
# This script intentionally does not start the old insecure single-process
# HTTP development topology.

Write-Host "VEILBENCH secure local run" -ForegroundColor Cyan
Write-Host "Use the documented Compose procedure in docs\PHASE_0_TO_4_DELIVERY.md." -ForegroundColor Yellow
Write-Host "It generates development certificates, starts PostgreSQL, and runs all three MPC parties." -ForegroundColor Yellow
exit 1
