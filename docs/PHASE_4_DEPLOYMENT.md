# VEILBENCH Phase 4 — Academic deployment runbook

This phase provides a repeatable deployment package for the agreed academic
configuration:

- Next.js frontend on Vercel's temporary `*.vercel.app` hostname.
- One low-cost Ubuntu LTS VPS running FastAPI, PostgreSQL, Caddy, and three
  separately configured MPyC party containers.
- Three founders submit independently and directly to their assigned party.
- Only Caddy publishes public ports. PostgreSQL, coordinator control traffic,
  party control routes, and MPyC peer sockets remain on private Docker networks.

**This runbook does not claim that a live cloud deployment has already happened.**
A VPS must be provisioned and Vercel must be linked to the user's account. Those
account, billing, SSH, and public-IP actions require the project owner.

## 1. Provision the VPS

Choose Ubuntu 24.04 LTS (64-bit) with a public IPv4 address. For the initial
three-party demonstration, use at least 2 vCPU, 4 GB RAM, and 40 GB SSD if the
budget permits. A smaller plan may work for light testing but must be measured
under a real MPyC run before the demonstration.

Configure the provider firewall/security group to allow only:

- TCP 22 (or your chosen SSH port), preferably restricted to your IP.
- TCP 80 (Caddy HTTP challenge and redirect).
- TCP 443 (HTTPS).
- UDP 443 (optional HTTP/3).

Do not open 5432, 8000, 8100, 11365, 11366, or 11367 to the public internet.
The production Compose file publishes only Caddy's 80/443 ports.

## 2. Upload the Phase 4 project ZIP

From Windows PowerShell, upload the downloaded archive (adjust the filename,
username, IP, and SSH port):

```powershell
scp .\VEILBENCH_phase4_deployment.zip ubuntu@YOUR_VPS_IP:/tmp/VEILBENCH_phase4_deployment.zip
```

SSH to the VPS and extract it:

```bash
sudo mkdir -p /opt
sudo unzip /tmp/VEILBENCH_phase4_deployment.zip -d /opt
sudo chown -R "$USER":"$USER" /opt/VEILBENCH
cd /opt/VEILBENCH
```

The ZIP intentionally excludes `.env` files, certificates/private keys, Git
metadata, local party state databases, Python virtual environments, and
`node_modules`. Do not upload a development `.env` or local certificate folder.

## 3. Install Docker on Ubuntu

Run the included bootstrap script:

```bash
sudo bash scripts/bootstrap_ubuntu_vps.sh
```

If you want the script to configure UFW as well, first confirm your SSH port
and then run:

```bash
sudo bash scripts/bootstrap_ubuntu_vps.sh --configure-firewall --ssh-port 22
```

Replace `22` if your SSH daemon uses another port. The script allows SSH before
enabling UFW, but also configure the provider firewall/security group. Docker's
published ports are controlled separately from ordinary UFW application rules;
this stack deliberately publishes only the Caddy edge.

## 4. Deploy the frontend once to obtain its stable Vercel origin

On the Windows development machine, from the project folder:

```powershell
cd frontend
# One-time only after the Next.js 16 dependency migration:
npm install
npm audit
npm audit --omit=dev
npm run lint
npm run typecheck
npm run build
# Once package-lock.json has been regenerated and verified, future clean installs use npm ci.
npx vercel login
npx vercel link
npx vercel --prod
```

This first deployment reserves the stable production `https://<project>.vercel.app`
hostname. The public API variables can be configured after the VPS IP is known.
The first temporary deployment may display a configuration warning because its
public API endpoints have not been set yet; it is only used to establish the
stable Vercel project origin.

Keep using the same linked Vercel project and production hostname. Do not use a
preview deployment URL as `FRONTEND_PUBLIC_URL` unless you intentionally add
that exact preview origin to the backend and party CORS allowlists.

## 5. Generate production environment and internal certificates

On the VPS, from `/opt/VEILBENCH`, generate the private production environment
file using the actual public IPv4 and the exact Vercel production origin:

```bash
python3 scripts/generate_production_env.py \
  --vps-ip YOUR_VPS_PUBLIC_IPV4 \
  --frontend-origin https://YOUR_PROJECT.vercel.app
```

The default temporary DNS suffix is `sslip.io`. It generates one API hostname
and three party hostnames from the VPS IPv4 address. If that DNS service is
unavailable, the helper supports `--dns-suffix nip.io`.

The helper creates distinct high-entropy secrets and refuses to overwrite an
existing `.env.production`. Do not use `--force` during routine deployment; it
rotates application secrets and may invalidate founder capabilities.

Generate the internal CA, API, coordinator, dedicated edge client, party-control, and MPyC certificates:

```bash
python3 scripts/generate_certs.py
sudo bash scripts/secure_production_certs.sh
```

The certificate permission script:

- Keeps `ca/ca.key` root-owned with mode 0600.
- Assigns backend and party runtime private keys to UID/GID 10001 with mode 0600.
- Creates a dedicated `edge/edge.crt` and `edge/edge.key` client identity for Caddy.
- Keeps the edge key root-owned with mode 0600 because the hardened Caddy container runs as root with all capabilities dropped except `NET_BIND_SERVICE`.
- Creates `infrastructure/certs/edge/ca.crt` for Caddy.
- Gives Caddy only the public CA certificate and its dedicated edge client identity; it never mounts the CA private key or coordinator private key.

Production Uvicorn listeners require a CA-signed client certificate (`--ssl-cert-reqs 2`). The backend presents the coordinator client certificate to parties; Caddy presents the separate edge client certificate to the backend and party public-input listeners. The deployment preflight runs `python -m backend.ops.smoke_test_internal_mtls` inside the backend container to verify that trusted clients succeed and anonymous TLS clients are rejected.

The production network is segmented: PostgreSQL and the backend share `database-internal`; the backend and Caddy share `backend-edge`; the backend, parties, and Caddy share `mpc-internal`; only Caddy joins `public-edge`. Caddy therefore has no network path to PostgreSQL.

Do not copy the CA private key into a container or Vercel. Caddy uses its own
persistent ACME state for browser-trusted public certificates.

## 6. Configure Vercel's four public environment variables

On the VPS, print only the public URL variables (these contain no secrets):

```bash
grep '^NEXT_PUBLIC_' .env.production
```

In the Vercel project settings, add these four values to the **Production**
environment:

- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_PARTY_0_URL`
- `NEXT_PUBLIC_PARTY_1_URL`
- `NEXT_PUBLIC_PARTY_2_URL`

Use the exact HTTPS values printed from `.env.production`. Never add the
coordinator admin token, founder signing secrets, party control tokens, or
PostgreSQL credentials to Vercel. They belong only in the private VPS
`.env.production` file and the scoped backend/party containers.

Redeploy the frontend after saving the variables:

```powershell
cd frontend
npx vercel --prod
```

Next.js embeds `NEXT_PUBLIC_*` variables into the browser bundle at build time.

## 7. Validate and deploy the VPS stack

From the VPS project root:

```bash
sudo python3 scripts/validate_production_env.py
```

This checks environment consistency, secret uniqueness/length, exact Vercel
origin alignment, database URL consistency, certificate chains, certificate
hostnames, certificate expiry, and private-key permissions. It never prints
secret values.

Then deploy:

```bash
sudo bash scripts/deploy_vps.sh
```

The deployment script performs these steps without deleting persistent volumes:

1. Revalidates the production environment and certificate tree.
2. Validates the Compose configuration.
3. Validates the Caddyfile using the same Caddy image as the stack.
4. Pulls PostgreSQL and Caddy, then builds the backend and three party images
   sequentially to limit peak memory use on the low-cost VPS.
5. Starts the services with `up -d --no-build`, preserving named volumes.
6. Waits for public HTTPS readiness and runs read-only smoke tests.

The deployment helper runs `scripts/build_production_images.sh` before
`docker compose up -d --no-build --remove-orphans`. It does not run `down -v`,
delete volumes, or rotate secrets. See the Phase 6 guide for the explicit
synthetic three-founder end-to-end MPC test.

## 8. Verify the public endpoints

The deployment script automatically runs `scripts/smoke_test_public.py`. To
rerun it manually, use the API and party URLs from `.env.production`:

```bash
python3 scripts/smoke_test_public.py \
  --api-url https://api.YOUR_VPS_IP.sslip.io \
  --party-0-url https://party0.YOUR_VPS_IP.sslip.io \
  --party-1-url https://party1.YOUR_VPS_IP.sslip.io \
  --party-2-url https://party2.YOUR_VPS_IP.sslip.io \
  --frontend-origin https://YOUR_PROJECT.vercel.app
```

The smoke test checks:

- Coordinator readiness (including PostgreSQL availability).
- Correct identity and MPyC TLS-enabled flag for all three parties.
- CORS preflight from the exact Vercel origin.
- Founder input routes are reachable but reject requests without a valid
  capability.
- Party status and compute control routes remain hidden by Caddy.

The smoke test does **not** create a session, submit a salary, or start MPC.

## 9. Perform the real three-founder demonstration

Only after public smoke tests pass:

1. Open the Vercel management page.
2. Enter the coordinator admin token locally in the management UI. Retrieve it
   from the VPS terminal if necessary, but never paste it into a chat or commit it.
3. Create a benchmark session.
4. Distribute each founder's submission page and one-time capability separately.
5. Open three separate browser sessions (or devices), one per founder.
6. Submit synthetic academic demo values, for example 50,000; 70,000; and 60,000.
7. Confirm the dashboard reports three received submissions.
8. Initiate computation and verify the expected aggregate 180,000 and average
   60,000.0.
9. Verify that no individual salary appears in coordinator responses or logs.

Use synthetic values for the public demonstration. The three containers share
one VPS and one administrator; this demonstrates the MPC workflow, not
independent organizational trust or protection from the VPS administrator.

## 10. Backups and safe operations

Create a database backup:

```bash
sudo bash scripts/backup_postgres.sh
```

Backups are stored under `backups/` with restrictive permissions. Copy them to
separate trusted storage; a backup on the same VPS does not protect against VPS
loss. Test restoration before relying on the backup process. A restore is
destructive and requires explicit confirmation:

```bash
sudo env CONFIRM_RESTORE=YES bash scripts/restore_postgres.sh backups/your-backup.dump
```

Routine stop/start operations preserve all named volumes:

```bash
sudo docker compose --env-file .env.production -f docker-compose.production.yml down
sudo docker compose --env-file .env.production -f docker-compose.production.yml up -d
```

**Never use `docker compose down -v` for routine maintenance.** It deletes the
PostgreSQL data, party replay/tombstone state, and Caddy ACME certificate state.

Useful diagnostics:

```bash
sudo docker compose --env-file .env.production -f docker-compose.production.yml ps
sudo docker compose --env-file .env.production -f docker-compose.production.yml logs --tail=150 veilbench-backend veilbench-edge
sudo docker compose --env-file .env.production -f docker-compose.production.yml exec veilbench-backend alembic current
```

## 11. Deployment completion criteria

Do not describe VEILBENCH as publicly deployed or fully verified until all of
these have actually passed on the target VPS and Vercel project:

- Docker Compose config and image builds succeed on the VPS.
- Alembic migrations apply to PostgreSQL.
- Caddy obtains public certificates for the API and all party hostnames.
- Public proxy blocks party control/compute routes.
- CORS succeeds from the exact Vercel origin.
- Three founder browsers submit directly to their assigned party endpoints.
- The coordinator receives no plaintext salary values.
- All three MPyC parties complete the real computation and agree on the result.
- PostgreSQL and party replay state survive a controlled container restart.
- Backup restore is tested.

A successful build or health check alone is not proof of a complete MPC deployment. The internal mTLS smoke test must pass, and the edge container must not share the PostgreSQL-only network.
