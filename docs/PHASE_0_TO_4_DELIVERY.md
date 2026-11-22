# VEILBENCH Phases 0–4 delivery status

## Implemented in this source tree

1. **Private per-founder submission:** the only salary route is
   `POST /sessions/{session_id}/input` on an assigned party. It requires a
   short-lived HMAC capability scoped to exactly one party and one session.
   The coordinator API intentionally has no salary field or submission route.
2. **Real MPC:** each party launches `backend.mpc.party_runner` with its own
   input, party index, and peer configuration. `backend.mpc.protocol` uses
   `mpc.input`, addition of secret shares, and `mpc.output` only for the public
   sum.
3. **Session/database layer:** async SQLAlchemy creates a PostgreSQL
   `benchmark_sessions` table containing session state, submission metadata,
   expiry, aggregate, and average only. It has no columns for salaries,
   capabilities, shares, or private keys.
4. **Transport configuration:** Docker Compose uses HTTPS for backend/party
   services and MPyC `--ssl` for P2P traffic. MPyC certificates are named and
   issued specifically for MPyC's fixed `MPyC party <id>` hostname check.
5. **Frontend flow:** management creates three separate invites. A founder
   page sends the salary directly from the browser to the configured party URL
   and clears both input and capability from its component state afterwards.
6. **Durable party replay guards:** each party has its own SQLite state file,
   stored on a separate Docker named volume (or under `.state/` for the Windows
   launcher). It stores only session IDs, expiry timestamps, submission flags,
   and lifecycle markers—not salaries, tokens, shares, or results. A unique
   session row makes each founder capability single-use across party restarts.
7. **Cleanup and recovery:** party services periodically purge expired
   in-memory inputs. The coordinator waits for all compute requests to settle,
   retries idempotent party shutdown up to three times, and keeps the global
   computation barrier if any party cannot confirm cleanup. The admin-only
   `POST /api/v1/sessions/{session_id}/recover` endpoint retries cleanup and
   releases that barrier only after all three parties confirm.

## Exact PowerShell commands (lightweight, no Docker)

Run these from the extracted project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
python -m compileall -q backend
python -m pytest backend\tests\test_health.py backend\tests\test_tokens.py backend\tests\test_mpyc_protocol.py -q
Set-Location frontend
npm ci
npm run build
Set-Location ..
```

The real three-party MPyC test uses local plaintext loopback sockets in this
lightweight command. It verifies the MPyC computation but does **not** verify
the Compose TLS wiring.

## Exact PowerShell commands (full local Compose attempt)

Docker Desktop must be running. This creates local development certificates
and a local `.env`; do not commit either output.

```powershell
.\.venv\Scripts\Activate.ps1
python scripts\generate_certs.py
Copy-Item .env.example .env
$secrets = 1..8 | ForEach-Object { python -c "import secrets; print(secrets.token_urlsafe(32))" }
$envFile = Get-Content .env
$envFile = $envFile -replace 'CHANGE_ME_URL_SAFE_DATABASE_PASSWORD', $secrets[0]
$envFile = $envFile -replace 'CHANGE_ME_RANDOM_ADMIN_TOKEN', $secrets[1]
$envFile = $envFile -replace 'CHANGE_ME_RANDOM_FOUNDER_SIGNING_SECRET_0', $secrets[2]
$envFile = $envFile -replace 'CHANGE_ME_RANDOM_FOUNDER_SIGNING_SECRET_1', $secrets[6]
$envFile = $envFile -replace 'CHANGE_ME_RANDOM_FOUNDER_SIGNING_SECRET_2', $secrets[7]
$envFile = $envFile -replace 'CHANGE_ME_RANDOM_PARTY_0_CONTROL_TOKEN', $secrets[3]
$envFile = $envFile -replace 'CHANGE_ME_RANDOM_PARTY_1_CONTROL_TOKEN', $secrets[4]
$envFile = $envFile -replace 'CHANGE_ME_RANDOM_PARTY_2_CONTROL_TOKEN', $secrets[5]
Set-Content -Path .env -Value $envFile
docker compose config
docker compose up --build
```

For a local browser to trust the generated development CA, import
`infrastructure\certs\ca\ca.crt` into the appropriate trusted-root store, or
use a certificate issued by a CA already trusted by the browser. Do this only
for the local development CA you generated yourself.

Once Compose starts, open `http://localhost:3000`, enter the admin token from
`.env`, create a session, distribute each page link and token to its intended
founder, submit three values, refresh the manager page, and click **Compute
aggregate**. The expected aggregate for 50,000, 70,000, and 60,000 is 180,000
and the expected average is 60,000.

## Verification performed by this delivery

The package records only checks actually run for this delivery in
`CHANGELOG.md`. Re-run the commands above on the target Windows machine before
claiming live readiness.

## Not yet verified / deployment limitations

The limitations below describe the earlier Phase 0–4 baseline. Phase 5 adds a
production-only mTLS listener policy, dedicated Caddy client identity, and
network segmentation, but those changes still require live Docker/VPS
verification before they can be treated as deployed controls.

- A full Docker Compose run has not been performed here, so PostgreSQL schema
  startup, browser CORS, certificate mounts, HTTPS trust, three-node MPyC
  mTLS, and end-to-end UI/session behavior remain live-integration checks.
- Local async HTTP and real MPyC subprocess tests now pass with permission
  to use loopback sockets. These tests do not establish deployed TLS security
  or PostgreSQL concurrency behavior.
- The generated CA and certificates are self-signed development material. A
  production deployment needs a managed PKI, certificate rotation, secure
  key storage, and a browser-trusted HTTPS frontend/reverse proxy.
- The original development party HTTPS listener used server-authenticated
  TLS plus party-specific bearer control tokens. The Phase 5 production
  Compose profile now passes `--ssl-cert-reqs 2` to the backend and all party
  listeners, uses separate coordinator and Caddy client certificates, and
  includes an internal mTLS smoke test. The local development Compose profile
  remains compatible with direct browser HTTPS and does not enforce client
  certificates.
- The original development Compose file publishes party HTTPS ports for
  direct browser submissions. The production Compose profile instead exposes
  only Caddy's 80/443 ports and restricts public party routes to founder input
  and health. This configuration still requires live Docker/Caddy validation.
- The Compose nodes run on one host. They have process isolation only; they do
  not provide the independent administrative domains required for the strongest
  MPC trust model.
- The party replay guard is durable on the configured SQLite volume, but the
  salary itself remains volatile. If a party restarts after receiving an input,
  its persistent marker is changed to `FAILED`; the input cannot be replayed and
  the coordinator requires a fresh benchmark session. Do not delete or replace
  the per-party state volumes while sessions are active.
- This project documents passive honest-but-curious security for $t=1$ of 3.
  It does not claim malicious-security or Byzantine-fault tolerance.

## Interrupted computation recovery

Admission uses a PostgreSQL transaction advisory lock and a persisted
`computing` row to prevent overlapping runs on the fixed three-party ports.
A timeout or coordinator crash deliberately leaves this barrier in place.
Do not clear it manually while any old MPC process could still be running.

After the party services are reachable again, use the authenticated recovery
endpoint. It retries each party's idempotent shutdown and marks the session
failed only after all three persistent tombstones are confirmed:

```powershell
$headers = @{ "X-VEILBENCH-Admin-Token" = "<ADMIN_TOKEN>" }
Invoke-RestMethod -Method Post -Uri "https://localhost:8000/api/v1/sessions/<SESSION_ID>/recover" -Headers $headers
```

Replace `<SESSION_ID>` with the affected session ID. If any party remains
unreachable, the endpoint returns an error and the `computing` barrier remains
in place. Restore or restart that party with its original persistent state
volume, then retry. If the party's state volume has been lost, do not manually
clear the barrier until an operator has independently verified that every old
MPyC child process is stopped. After recovery, create a fresh session because
private inputs are intentionally not persisted. Cross-worker locking and this
recovery path still require a live PostgreSQL/Docker integration test.
