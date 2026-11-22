# VEILBENCH — Distributed MPC Infrastructure Specification

> **Implementation note (current revision):** consult
> `PHASE_0_TO_4_DELIVERY.md` for the authoritative implemented flow and live
> verification status. This document includes design rationale and some
> forward-looking deployment guidance; it is not evidence that an environment
> has completed a live mTLS or multi-host test.

## 1. Executive Summary & Architectural Overview

VEILBENCH transitions from a single-machine subprocess architecture to a **distributed microservice architecture** using containerization and independent network topologies.

In this model, each of the three startup founders is represented by a dedicated, isolated compute container:
- `veilbench-mpc-node0` (Founder 1 / Party 0)
- `veilbench-mpc-node1` (Founder 2 / Party 1)
- `veilbench-mpc-node2` (Founder 3 / Party 2)

Each container hosts an isolated instance of the VEILBENCH Party Service (`backend.mpc.party_service`), maintaining its own memory space, authentication token, lifecycle state machine, and communication channels. Each party also has a distinct persistent SQLite replay-guard volume. That store contains only session identifiers, expiry timestamps, and lifecycle markers; it never stores founder salaries, capability tokens, MPyC shares, or aggregate results.

```
                      ┌──────────────────────────────────────────────┐
                      │              FastAPI Backend /               │
                      │            Distributed Coordinator           │
                      └───────┬──────────────┬──────────────┬────────┘
                              │              │              │
                   POST /input│   POST /input│   POST /input│
               (Founder 1 val)│(Founder 2 val│(Founder 3 val│
                              ▼              ▼              ▼
                     ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
                     │ MPC Node 0  │   │ MPC Node 1  │   │ MPC Node 2  │
                     │ (Party 0)   │   │ (Party 1)   │   │ (Party 2)   │
                     │ Port: 8100  │   │ Port: 8100  │   │ Port: 8100  │
                     └──────▲──────┘   └──────▲──────┘   └──────▲──────┘
                            │                 │                 │
                            └─────────┬───────┴────────┬────────┘
                                      │  Peer-to-Peer  │
                                      │  MPyC Network  │
                                      │  (Ports 11365+)│
                                      └────────────────┘
```

---

## 2. Trust Model: Processes vs. Independent Infrastructure

> [!WARNING]
> **CRITICAL SECURITY NOTE & RULE 20 COMPLIANCE (Honest Limitations):**
> Docker containers running on a single host machine **DO NOT** provide independent organizational trust or Byzantine fault tolerance.

### 2.1 The Academic vs. Real-World Reality

| Property | Single-Host Containers (Local Development) | True Multi-Organization Deployment |
| :--- | :--- | :--- |
| **Physical Isolation** | Shared hardware, CPU, RAM, host kernel | Physically distinct servers / cloud accounts |
| **Root Administrator** | Single host `root` can inspect all container RAM | No single party has administrative control over peers |
| **Network Snooping** | Docker bridge inspectable via host `tcpdump` | Public internet with authenticated mutual TLS |
| **Adversarial Model** | Passive / honest-but-curious demo simulation | Cryptographic threshold trust across legal boundaries |

### 2.2 Why Docker Containers on One Machine Cannot Guarantee Cryptographic Privacy
1. **Host Memory Snooping:** A compromised host administrator can attach a debugger or dump memory (`/proc/<pid>/mem`) of all three containers, recovering all plaintext inputs simultaneously.
2. **Side-Channel Vulnerabilities:** Shared CPU caches allow cache-timing attacks across container boundaries.
3. **Collusion Simulation:** In our local Docker Compose setup, the backend coordinator holds the auth tokens for all three nodes. In a true sovereign deployment, each founder would host their node in their own AWS/GCP account or physical on-premise infrastructure, holding their own private keys.

---

## 3. Party Lifecycle State Machine

Each party strictly follows a deterministic 7-state lifecycle governed by `backend.mpc.lifecycle.PartyLifecycle`:

```
               ┌───────────────┐
               │  INITIALIZING │
               └───────┬───────┘
                       │ Valid configuration loaded
                       ▼
         ┌───────────────────────────┐
         │  WAITING_FOR_PARTICIPANTS │◄────── [Submits Input (1-time only)]
         └─────────────┬─────────────┘
                       │ All parties confirmed submitted
                       ▼
                  ┌─────────┐
                  │  READY  │
                  └────┬────┘
                       │ Coordinator triggers /compute
                       ▼
                ┌─────────────┐
    ┌───────────┤  COMPUTING  ├───────────┐
    │           └──────┬──────┘           │
    │ Failure          │ Success          │ Timeout /
    │                  ▼                  │ Connection drop
    │            ┌───────────┐            │
    │            │ COMPLETED │            │
    │            └─────┬─────┘            │
    ▼                  │                  ▼
┌────────┐             │             ┌────────┐
│ FAILED │◄────────────┴────────────►│ FAILED │
└───┬────┘                           └───┬────┘
    │ Graceful cleanup                   │ Graceful cleanup
    ▼                                    ▼
┌──────────────────────────────────────────────┐
│                   SHUTDOWN                   │
└──────────────────────────────────────────────┘
```

### Transition Invariants
- **Double Submission Prevention:** Calling `mark_input_submitted()` a second time raises an explicit `ValueError`, returning HTTP 409 Conflict.
- **Strict State Enforcement:** Parties cannot skip states (e.g., `INITIALIZING -> COMPUTING` is rejected).
- **Zero Sensitive Data Logging:** State changes, timestamps, and uptime are logged, but salary values and secret polynomial shares are **never** included in log entries or state dictionaries.

---

## 4. TLS & Certificate Lifecycle Management

Mutual TLS (mTLS) secures inter-party communications over the MPyC socket layer. The original local development party HTTPS listener used server-authenticated TLS plus a party-specific bearer control token. The Phase 5 production Compose profile additionally requires client certificates on party and backend HTTPS listeners: the coordinator uses its dedicated client identity, and Caddy uses a separate edge identity to proxy public founder-input requests. The local development Compose profile intentionally remains compatible with browser-to-party HTTPS without client certificates.

### 4.1 Certificate Hierarchy
- **Certificate Authority (CA):** Self-signed root CA created for the session or cluster (`VEILBENCH-MPC-CA`).
- **Party Certificates:** Individual RSA-2048 certificates with Subject Alternative Names (`DNS:veilbench-mpc-node0`, `IP:127.0.0.1`, `DNS:localhost`).

### 4.2 Lifecycle Phases

1. **Generation (`scripts/generate_certs.py`):**
   - Root CA key and self-signed certificate are generated with 365-day validity.
   - Individual private keys (`party_{i}.key`) and CSRs (`party_{i}.csr`) are generated.
   - CA signs the party certificates with extended key usage (`serverAuth,clientAuth`).
2. **Distribution:**
   - In Docker Compose, the CA certificate (`ca.crt`) is mounted read-only into `/app/certs/ca:ro` across all nodes.
   - Each node receives **ONLY** its own private key and certificate into `/app/certs/party:ro`. Nodes do **NOT** have access to peer private keys.
3. **Private Key Storage:**
   - Keys reside in container memory or read-only volume mounts with strict UNIX permissions (`0600`).
4. **Validation:**
   - MPyC peer connections verify peer certificates against the mounted `ca.crt`.
5. **Rotation & Revocation:**
   - To rotate certificates, new certificates are issued by the CA and mounted into the containers with a rolling restart.
   - In an enterprise PKI, a Certificate Revocation List (CRL) or OCSP stapling would be queried.
6. **Session Cleanup:**
   - Upon session termination (`POST /shutdown`), volatile memory holding inputs and temporary session state is purged.
   - A durable tombstone remains in that party's SQLite state volume until the founder capability expires, preventing replay after shutdown or process restart.
   - A background expiry task purges expired in-memory session data and removes expired replay guards.
   - If a party restarts while a founder input was in memory, its persistent guard is marked `FAILED`; the old capability remains consumed and the coordinator requires a new session.
   - The coordinator retries shutdown and keeps its persisted computation-admission barrier if cleanup cannot be confirmed. An authenticated recovery endpoint retries the cleanup; it does not force-clear the barrier.

---

## 5. Network Isolation & Docker Topology

The `docker-compose.yml` configures two isolated bridge networks:
1. `veilbench-net`: Front-facing network connecting the Next.js frontend, FastAPI backend, and PostgreSQL database.
2. `mpc-internal-net`: An **internal-only** network (`internal: true`) connecting the backend coordinator and the 3 MPC party nodes.
   - Nodes cannot communicate with external internet or the database directly.
   - Port forwarding is strictly limited: only internal ports `8100` (HTTP control) and `11365+` (MPyC P2P) are accessible within `mpc-internal-net`.

---

## 6. Failure Handling & Timeouts

1. **Input Submission Timeout:** If a founder fails to submit their input within the timeout window (15s default), the session aborts and transitions to `FAILED`.
2. **Computation Deadlock Prevention:** All peer connections have an explicit socket timeout. If an MPC process drops or hangs, `asyncio.wait_for` terminates the execution, kills orphaned child processes, and releases network sockets.
3. **Graceful Shutdown:** The coordinator waits for all three compute requests to settle, then retries `/shutdown` on parties that have not confirmed cleanup. A successful response also records a durable replay tombstone. If any party cannot be reached, the coordinator keeps the global computation barrier until authenticated recovery confirms all three parties are cleared.
