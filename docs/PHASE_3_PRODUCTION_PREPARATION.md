# VEILBENCH Phase 3 — Production preparation

This phase prepares the academic demonstration for one low-cost Linux VPS, a Vercel-hosted
Next.js frontend, one FastAPI coordinator, three Dockerized MPyC party processes, PostgreSQL,
and Caddy as the only public ingress. It does not deploy the application.

## 1. Deployment shape and trust boundary

- Vercel hosts the Next.js frontend.
- One Linux VPS hosts PostgreSQL, FastAPI, three MPyC party containers, and Caddy.
- Only Caddy publishes host ports 80 and 443.
- PostgreSQL, FastAPI, party control endpoints, and MPyC peer ports are not published to the VPS host.
- Caddy exposes only `/api/v1/*` on the API hostname, and only `POST/OPTIONS /sessions/{uuid}/input` plus `GET /health` on each party hostname.
- Party `/status`, `/compute`, `/result`, and `/shutdown` routes remain reachable only from the private Docker network.
- In the original Phase 3 topology, the coordinator connected to party control services over HTTPS, the internal CA, and party-specific bearer tokens, but the party HTTPS listener did not require a client certificate. Phase 5 closes that gap in the production Compose profile: Uvicorn requires a CA-signed client certificate, the coordinator presents its dedicated client identity, and Caddy presents a separate edge identity for the public founder-input proxy. The local development Compose profile remains easier to run and does not enforce client certificates on its HTTPS listener.
- MPyC peer sockets use the separate party certificates and mutually authenticated TLS configuration.

All three parties still share one VPS and one administrator. This is an academic demonstration of the protocol and direct-input workflow, not three independent organizations or protection from a VPS administrator.

## 2. Temporary HTTPS hostnames

The included helper uses `sslip.io` names based on the VPS public IPv4 address, for example:

- `api.203.0.113.10.sslip.io`
- `party0.203.0.113.10.sslip.io`
- `party1.203.0.113.10.sslip.io`
- `party2.203.0.113.10.sslip.io`

The addresses above are documentation examples only. Use the actual public IP assigned to the VPS. The `anything.<IPv4>.sslip.io` hostname form resolves to the embedded public IP, including named prefixes such as `api.` and `party0.`. See the [sslip.io overview](https://nip.io/) for supported hostname forms.

`sslip.io` is a third-party public DNS service. Its availability and policies are outside VEILBENCH's control. Caddy will request publicly trusted certificates automatically, but issuance still depends on working public DNS, reachable ports 80/443, and certificate-authority policy/rate limits. Test certificate issuance before distributing founder links. If issuance fails, try the alternate `nip.io` suffix or use a domain you control. Do not disable HTTPS for founder submission. See [Caddy's upstream TLS trust configuration](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy) for the internal CA verification used by this deployment.

## 3. VPS prerequisites

Use a supported 64-bit Ubuntu LTS image. For the initial low-cost demonstration, start with at least 2 vCPU and 4 GB RAM if available; MPyC uses multiple Python processes, so verify memory and CPU during the actual three-party test before selecting a smaller plan.

Install Docker Engine and the Docker Compose plugin from Docker's official repository. Configure the VPS firewall/security group to allow only:

- TCP 22 (preferably restricted to your own IP)
- TCP 80
- TCP 443
- UDP 443 (optional HTTP/3)

Do not open TCP 5432, 8000, 8100–8102, or 11365–11367 to the public internet. The production Compose file does not publish these ports.

## 4. Create production environment values

From the project root on the VPS, first identify the public IPv4 and the final Vercel production origin. Deploy the frontend to Vercel before generating this file so that the exact `https://<project>.vercel.app` origin is known.

Run:

```bash
python3 scripts/generate_production_env.py \
  --vps-ip YOUR_VPS_PUBLIC_IPV4 \
  --frontend-origin https://YOUR_PROJECT.vercel.app
```

If you prefer the alternate temporary DNS suffix, add `--dns-suffix nip.io`.

The helper creates `.env.production` with seven distinct high-entropy application secrets and a URL-safe database password. It sets file permissions to `0600` where supported. It refuses to overwrite an existing file unless `--force` is supplied. Do not use `--force` during normal deployment: it rotates all application secrets. If a database volume already exists, changing `POSTGRES_PASSWORD` in the file does not change the password stored inside PostgreSQL; coordinate a database `ALTER ROLE` and service restart as part of a planned credential rotation.

Keep `.env.production` private and outside Git. Never put `COORDINATOR_ADMIN_TOKEN`, founder signing secrets, party control tokens, or database credentials in Vercel `NEXT_PUBLIC_*` variables.

## 5. Generate and secure internal certificates

Generate the internal CA and service/MPyC certificates on the VPS:

```bash
python3 scripts/generate_certs.py
sudo bash scripts/secure_production_certs.sh
```

The script assigns backend and party runtime certificate/key files to UID/GID 10001 with restrictive permissions. The CA private key remains root-owned with mode `0600`; it is not mounted into any runtime container. Caddy receives a separate root-owned edge client key plus the public CA certificate, never the CA private key or coordinator private key. The secure script creates a separate `infrastructure/certs/public-ca/` directory for Caddy so the edge container never mounts the directory containing `ca.key`. See Phase 5 for the enforced production mTLS topology and existing-environment migration.

The generated certificates are for the private Docker control/MPyC network. Caddy obtains separate publicly trusted certificates for the browser-facing hostnames and renews those through its persistent `/data` volume. The internal certificates have a finite validity period (365 days by default); internal CA/service-certificate rotation is a manual maintenance task and must be completed before expiry. The generator reuses existing certificate files, so do not assume rerunning it rotates an existing certificate set.

## 6. Configure Vercel

In the Vercel project's Production Environment Variables, set the four public values from `.env.production`:

- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_PARTY_0_URL`
- `NEXT_PUBLIC_PARTY_1_URL`
- `NEXT_PUBLIC_PARTY_2_URL`

These values are public endpoint URLs, not credentials. Redeploy the frontend after changing them because Next.js embeds `NEXT_PUBLIC_*` values at build time.

The coordinator's `FRONTEND_PUBLIC_URL`, `ALLOWED_ORIGINS`, and `MPC_PARTY_ALLOWED_ORIGINS` must contain the exact same Vercel production origin. Preview deployments are not automatically trusted; add a specific preview origin only when needed and understood.

The coordinator admin token is entered by the operator in the management UI at runtime. Do not configure it as a `NEXT_PUBLIC_*` variable and do not store it in source code.

## 7. Validate and start the VPS stack

From the project root:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml config --quiet
```

After generating the internal CA, validate the Caddyfile using the exact image version used by the stack:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml run --rm --no-deps --entrypoint caddy veilbench-edge validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

If both validations succeed, build and start:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build
```

The production Compose file deliberately does not attach the whole `.env.production` file to every container. PostgreSQL receives only its database credentials; each party receives only its own founder-signing secret and control token; the coordinator receives the three founder secrets and three party control tokens it needs; Caddy receives only public hostnames. The VPS administrator and Docker daemon remain trusted parts of this single-host academic deployment.

The backend container validates production settings, applies `alembic upgrade head`, and then starts FastAPI. Production requires `DATABASE_AUTO_CREATE=false`; schema creation is managed by migrations rather than `create_all`.

Check services and logs:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml ps
```

```bash
docker compose --env-file .env.production -f docker-compose.production.yml logs --tail=150 veilbench-backend veilbench-edge
```

Check migration state:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml exec veilbench-backend alembic current
```

Check public readiness:

```bash
curl --fail https://$(grep '^VEILBENCH_API_HOST=' .env.production | cut -d= -f2)/health/ready
```

Do not call the deployment complete until a real three-founder browser submission and a real MPyC computation succeed over the public HTTPS endpoints.

## 8. Database backups

Create an encrypted/off-host backup plan before collecting real demonstration data. A local backup can be generated with:

```bash
sh scripts/backup_postgres.sh
```

The script creates a mode-`0600` custom-format dump under `backups/`. Copy backups to a separate trusted location; a backup on the same VPS is not protection against VPS loss. Do not commit backups. Test restoration before relying on the backup process.

Party SQLite state volumes contain replay/tombstone metadata, not salary inputs. They are also persistent Docker volumes. Do not run `docker compose down -v` unless intentionally deleting the database and party state.

## 9. Operational commands

Start/update:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build
```

Stop without deleting volumes:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml down
```

Follow logs:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml logs -f
```

Backup:

```bash
sh scripts/backup_postgres.sh
```

Do not use `down -v` for routine shutdowns.

## 10. Existing database migration note

A new production database is initialized with `alembic upgrade head`. If importing a database previously created by `Base.metadata.create_all`, back it up first and compare its table/column/index definitions with the initial migration. Only if it exactly matches the migration's initial schema should an administrator baseline it with `alembic stamp 0001_initial`; otherwise write and apply a real migration. Never stamp an unverified schema.

## 11. Release gates still required

This phase adds deployment configuration but does not claim a live deployment. Before release, verify:

1. Docker Compose config and all images build on the target VPS.
2. PostgreSQL readiness and Alembic migration succeed.
3. Caddy obtains and renews browser-trusted certificates.
4. Caddy blocks public party control routes while allowing only founder input and health.
5. CORS works from the exact Vercel origin.
6. Backend control requests validate the private CA and party tokens.
7. MPyC TLS peer sockets connect among all three containers.
8. Three separate browsers submit directly to their assigned parties.
9. The coordinator receives no plaintext salaries and only stores the aggregate/average.
10. Backup restoration is tested.

The local development Compose file remains available for the Windows workflow. Use `docker-compose.production.yml` only for the VPS topology.
