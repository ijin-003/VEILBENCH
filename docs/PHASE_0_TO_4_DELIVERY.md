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

- A full Docker Compose run has not been performed here, so PostgreSQL schema
  startup, browser CORS, certificate mounts, HTTPS trust, three-node MPyC
  mTLS, and end-to-end UI/session behavior remain live-integration checks.
- Local async HTTP and real MPyC subprocess tests now pass with permission
  to use loopback sockets. These tests do not establish deployed TLS security
  or PostgreSQL concurrency behavior.
- The generated CA and certificates are self-signed development material. A
  production deployment needs a managed PKI, certificate rotation, secure
  key storage, and a browser-trusted HTTPS frontend/reverse proxy.
- The Compose nodes run on one host. They have process isolation only; they do
  not provide the independent administrative domains required for the strongest
  MPC trust model.
- Party one-time-submission state is volatile. A party restart before cleanup
  loses that in-memory anti-replay marker; production needs durable,
  independently administered replay protection that still never stores salary.
- This project documents passive honest-but-curious security for $t=1$ of 3.
  It does not claim malicious-security or Byzantine-fault tolerance.

## Interrupted computation recovery

Admission uses a PostgreSQL transaction advisory lock and a persisted
`computing` row to prevent overlapping runs on the fixed three-party ports.
A timeout or coordinator crash deliberately leaves this barrier in place.
Do not clear it while any old MPC process could still be running.

For the supplied local Compose layout only:

```powershell
docker compose stop veilbench-backend veilbench-mpc-node0 veilbench-mpc-node1 veilbench-mpc-node2
docker compose ps -a
# Verify all four application services are stopped before the following command.
docker compose exec veilbench-db psql -U veilbench_user -d veilbench_db -c "UPDATE benchmark_sessions SET state='failed', failure_reason='Operator recovered stopped cluster' WHERE state='computing';"
docker compose start veilbench-mpc-node0 veilbench-mpc-node1 veilbench-mpc-node2 veilbench-backend
```

The database command assumes the username/database from `.env.example`;
substitute your configured values if different. Create a fresh session after recovery; party input is intentionally lost on
restart. This procedure has not been live-tested here. For remote deployment,
stop every coordinator worker and every party/child process before clearing
the barrier. Mock-based lifecycle tests do not prove cross-worker database
locking; that remains a required live PostgreSQL test.
