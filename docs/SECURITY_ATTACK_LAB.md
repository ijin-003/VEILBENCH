# VEILBENCH — Security Attack Demonstration Lab

## Purpose
This is a reproducible **negative-path security demonstration** for the academic three-founder MPC project. It runs real tests against the backend's authorization, invitation, token-scope and durable replay protections. Each run produces an offline **interactive HTML evidence board** plus machine-readable JSON and JUnit XML.

**Important:** The report is generated from genuine pytest results, not preprogrammed success animations. Several scenarios share the *same comprehensive test case*, and the interface discloses that grouping. A passing lab does not imply a live penetration test, separate MPC operators, or complete security assurance.

## Scope and execution

The lab operates exclusively on:
- FastAPI's in-process ASGI test transport (no external network requests)
- Temporary SQLite accounts and invitation records
- Temporary party replay-guard SQLite state
- Two disposable MPyC subprocesses in the disconnected-party test (local only)

It **never targets** the hosted Render service, Neon, Vercel, real accounts or real salaries. The no-third-party fault test checks *failure to complete*, not continuous availability.

```bash
python -m pip install -r backend/requirements.txt
python -m scripts.attack_lab --list
python -m scripts.attack_lab
# For one category, using the actual grouped security test:
python -m scripts.attack_lab --scenario token-tampering
```

Open `artifacts/attack-lab/index.html` locally. It contains **nine scenarios**, filterable by outcome with expandable ATTACK / DEFENSE / OBSERVATION / TEST EVIDENCE details. `report.json` gives the exact scenarios and status, and `pytest-results.xml` contains the original pytest records.

## Scenarios and observed expected controls

| Scenario | Attack type | Correct rejection / outcome |
|---|---|---|
| Role isolation | Founder attempts admin functions; admin requests founder assignment | HTTP 403 |
| Session expiry/revocation | Expired login; reuse after logout; expired benchmark | HTTP 401 / HTTP 410 |
| Invitation reuse/expiry | Activated once and replayed; expired invitation | First valid 200; replay/expired 400 |
| Tampered founder capability | Alter HMAC-protected token, use expired token | HTTP 403 |
| Cross-party/session | Apply founder capability to the wrong party/session | HTTP 403 |
| Duplicate submission | Repost salary using already-consumed capability | First valid 200; duplicate 409 |
| Durable replay | Retry after party module restart | HTTP 409 |
| Throttling | Repeated and rotated login/activation with forged forwarded headers | HTTP 429 with Retry-After |
| Missing party | Start only two of three required MPyC workers | Neither process should finish during bounded observation |

The rate-limit finding is tested against the actual throttle class, so it demonstrates process-local boundary logic rather than proving distributed IP controls or live load resilience.

## Security limitations to disclose
- All logical parties on Render Free share one host/operator; only **synthetic academic data** should be entered.
- The demo's independent-party confidentiality is not equivalent to production deployments using separately managed hosts, certificates and secrets.
- AuthThrottle stores process-local sliding windows, not a shared durable global rate limit.
- The missing-party test demonstrates **non-completion within a bounded window**: it is not an exhaustive denial-of-service or automatic recovery test.
- The JUnit report establishes tested checks at the commit shown in CI, not real-world coverage against all possible attacks.
- **Do not reproduce login flooding or denial-of-service tests against live Render.**

## Evidence for the viva
Show the generated `index.html`, select each attack category, state the attacker's objective and expected response, then show the matching test case and the original JUnit output. For live product demonstrations, run a normal authorized synthetic three-founder flow separately. Never display invitation tokens, bearer tokens, or individual salary submissions on slides.

## CI
The `.github/workflows/attack-lab.yml` workflow runs only on this development branch's PR or manual trigger and uploads `veilbench-attack-lab-evidence` artifacts. The live UI and homepage are not modified.
