"""VEILBENCH security attack demonstration lab.

Runs ONLY local pytest-based security probes against ASGI/SQLite and local
MPyC test processes. Produces evidence-based JSON and an offline interactive
HTML defense exhibit. It NEVER sends a request to Vercel, Render or Neon.

Usage:
    python -m scripts.attack_lab
    python -m scripts.attack_lab --list
    python -m scripts.attack_lab --scenario replay
    python -m scripts.attack_lab --output artifacts/attack-lab
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET


# Multiple scenarios can share a comprehensive test. That fact is displayed
# rather than falsely claiming they each ran as independent probes.
CASES = (
    {
        "id": "role-isolation", "title": "Unauthorized role escalation",
        "category": "AUTHORIZATION",
        "attack": "A signed-in founder tries to create/administer sessions and issue invitations; an admin requests a founder-only assignment.",
        "defense": "Role checks at authenticated API boundaries.",
        "expected": "HTTP 403 for unauthorized roles.",
        "test": "test_authenticated_roles_invitations_and_expiration",
        "file": "backend/tests/test_authenticated_security_boundaries.py",
    },
    {
        "id": "expired-session", "title": "Expired or revoked login",
        "category": "AUTHENTICATION",
        "attack": "A client reuses an expired bearer session, or uses its token again after logout.",
        "defense": "Expiry and persistent login-session revocation checks.",
        "expected": "HTTP 401 for expired and revoked credentials; HTTP 410 for an expired benchmark assignment.",
        "test": "test_authenticated_roles_invitations_and_expiration",
        "file": "backend/tests/test_authenticated_security_boundaries.py",
    },
    {
        "id": "invitation-abuse", "title": "Used or expired invitation",
        "category": "INVITATIONS",
        "attack": "An activation token is replayed after its first successful use; another invitation has already expired.",
        "defense": "Single-use hashed invitations with timestamps and account activation state.",
        "expected": "First valid activation HTTP 200; reused/expired activation HTTP 400.",
        "test": "test_authenticated_roles_invitations_and_expiration",
        "file": "backend/tests/test_authenticated_security_boundaries.py",
    },
    {
        "id": "token-tampering", "title": "Forged or altered founder capability",
        "category": "TOKEN INTEGRITY",
        "attack": "An attacker changes the HMAC-signed capability or attempts an expired capability.",
        "defense": "HMAC-SHA256 signature and expiry validation.",
        "expected": "HTTP 403; rejected salary never echoed in response.",
        "test": "test_founder_capability_scoping_and_replay_after_party_reload",
        "file": "backend/tests/test_authenticated_security_boundaries.py",
    },
    {
        "id": "wrong-party", "title": "Cross-party or cross-session submission",
        "category": "CAPABILITY SCOPE",
        "attack": "A founder attempts to submit a capability issued for a different party or benchmark session.",
        "defense": "Party- and benchmark-scoped signed capabilities.",
        "expected": "HTTP 403.",
        "test": "test_founder_capability_scoping_and_replay_after_party_reload",
        "file": "backend/tests/test_authenticated_security_boundaries.py",
    },
    {
        "id": "replay", "title": "Duplicate salary submission",
        "category": "REPLAY DEFENSE",
        "attack": "A valid founder submits a second salary through an already-consumed one-time capability.",
        "defense": "SQLite-backed unique submission claim and duplicate detection.",
        "expected": "First valid submission HTTP 200; second HTTP 409.",
        "test": "test_founder_capability_scoping_and_replay_after_party_reload",
        "file": "backend/tests/test_authenticated_security_boundaries.py",
    },
    {
        "id": "restart-replay", "title": "Replay after party restart",
        "category": "DURABLE REPLAY",
        "attack": "A previously used capability is retried after the simulated party module restarts.",
        "defense": "Durable on-disk replay tombstone survives loss of volatile process state.",
        "expected": "HTTP 409 on replay; no second salary is accepted.",
        "test": "test_founder_capability_scoping_and_replay_after_party_reload",
        "file": "backend/tests/test_authenticated_security_boundaries.py",
    },
    {
        "id": "rate-limit", "title": "Authentication request flooding",
        "category": "ABUSE CONTROLS",
        "attack": "Repeated login/activation requests, rotating usernames and forged X-Forwarded-For values.",
        "defense": "15-minute process-local sliding-window throttle per username, transport peer and global budget.",
        "expected": "HTTP 429 with Retry-After at configured thresholds.",
        "test": "test_unknown_username_is_limited_and_window_expires",
        "file": "backend/tests/test_http_security.py",
    },
    {
        "id": "missing-party", "title": "Missing MPC participant",
        "category": "AVAILABILITY",
        "attack": "Only two of three required real MPyC subprocesses are started.",
        "defense": "3-party protocol requires all parties; no aggregate is released.",
        "expected": "Neither worker completes successfully during the fault-injection observation window.",
        "test": "test_disconnected_party_handling",
        "file": "backend/tests/test_mpyc_protocol.py",
    },
)

THROTTLE_TESTS = (
    "test_unknown_username_is_limited_and_window_expires",
    "test_ip_bucket_ignores_spoofed_forwarded_header",
    "test_activation_is_throttled_separately_from_login",
    "test_global_bucket_limits_username_rotation",
)


def _test_nodes(selected: list[dict]) -> list[str]:
    nodes = {f"{case['file']}::{case['test']}" for case in selected}
    if any(case["id"] == "rate-limit" for case in selected):
        nodes.update(f"backend/tests/test_http_security.py::{name}" for name in THROTTLE_TESTS)
    return sorted(nodes)


def _outcomes(xml_path: Path) -> dict[str, dict]:
    root = ET.parse(xml_path).getroot()
    output: dict[str, dict] = {}
    for case in root.iter("testcase"):
        name = case.get("name", "")
        problems = [node.tag for node in case if node.tag in ("failure", "error", "skipped")]
        output[name] = {
            "status": "FAIL" if any(x in problems for x in ("failure", "error")) else "SKIP" if problems else "PASS",
            "duration_seconds": round(float(case.get("time", "0")), 3),
        }
    return output


def _render_html(report: dict) -> str:
    # All content is generated from fixed scenario definitions and pytest
    # outcomes; no credentials, salaries, tokens or tracebacks are embedded.
    rows = []
    for item in report["scenarios"]:
        status = item["status"]
        h = lambda key: html.escape(str(item[key]), quote=True)
        rows.append(f"""
        <article class="case" data-case="{h('id')}" data-status="{h('status')}">
          <button class="case-head" aria-expanded="false" type="button">
            <span class="case-index">{h('category')}</span>
            <strong>{h('title')}</strong>
            <span class="status {status.lower()}">{status}</span>
            <span class="arrow" aria-hidden="true">+</span>
          </button>
          <div class="case-body" hidden>
            <div class="detail"><small>ATTACK</small><p>{h('attack')}</p></div>
            <div class="detail"><small>DEFENSE</small><p>{h('defense')}</p></div>
            <div class="detail"><small>EXPECTED OBSERVATION</small><p>{h('expected')}</p></div>
            <div class="detail"><small>TEST EVIDENCE</small><p><code>{h('file')}::{h('test')}</code></p></div>
            <p class="caution">Grouped regression: multiple attack cases may be assertions in the same real test. No live attack was performed.</p>
          </div>
        </article>""")
    summary = report["summary"]
    tally = f"{summary['passed']}/{summary['total']}"
    generated = html.escape(report["generated_utc"])
    body = "\n".join(rows)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>VEILBENCH / ATTACK LAB</title><style>
:root{{--bg:#0b090a;--panel:#181112;--red:#eb1231;--ivory:#fff4e7;--muted:#baada8}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ivory);font:15px/1.5 system-ui,sans-serif}}
body:before{{content:"";position:fixed;inset:0;pointer-events:none;background:repeating-linear-gradient(111deg,transparent 0 115px,rgba(237,18,47,.025) 116px 117px);z-index:-1}}
header{{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:20px clamp(15px,4vw,55px);border-bottom:4px solid var(--red);background:#101011}}
.brand{{font:italic 900 25px Impact,"Arial Narrow",sans-serif;letter-spacing:-.03em}}.brand b{{color:var(--red)}}header span:last-child{{font-size:10px;letter-spacing:.18em;color:var(--muted)}}
main{{max-width:1240px;margin:0 auto;padding:clamp(20px,5vw,65px) 20px 70px}}
.eyebrow{{font-weight:900;letter-spacing:.24em;color:#ff6a78;font-size:11px}}h1{{margin:12px 0 6px;font:italic 900 clamp(54px,8vw,112px)/.9 Impact,"Arial Narrow",sans-serif;letter-spacing:-.025em}}h1 em{{color:var(--red);font-style:inherit}}
.lead{{max-width:780px;color:var(--muted);margin:19px 0 32px}}.metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:28px}}
.metric{{background:#171011;border-top:5px solid var(--red);padding:16px}}.metric b{{font:italic 900 clamp(26px,4vw,55px) Impact,sans-serif;display:block}}.metric small{{font-size:10px;font-weight:900;letter-spacing:.13em;color:var(--muted)}}
.toolbar{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:24px 0}}
.toolbar button{{border:1px solid #5d4044;background:var(--panel);color:var(--ivory);padding:10px 15px;font-weight:900;cursor:pointer;letter-spacing:.08em}}
.toolbar button:hover,.toolbar button[aria-pressed=true]{{background:var(--red);border-color:var(--red)}}button:focus-visible{{outline:3px solid #fff;outline-offset:3px}}
.case{{border:1px solid #49383a;margin:9px 0;background:linear-gradient(115deg,#171013,#0e0b0c)}}
.case-head{{display:grid;grid-template-columns:minmax(110px,180px) 1fr auto 22px;align-items:center;gap:18px;width:100%;background:transparent;color:var(--ivory);padding:22px;text-align:left;border:0;cursor:pointer}}
.case-head:hover{{background:#2c121a}}.case-index{{font-weight:900;font-size:10px;color:#f66370;letter-spacing:.12em}}.case-head strong{{font:italic 900 clamp(19px,2.4vw,30px)/1 Impact,"Arial Narrow",sans-serif;letter-spacing:.01em}}
.status{{font-size:10px;font-weight:900;padding:7px 12px;border:1px solid #77686a;letter-spacing:.08em}}.status.pass{{border-color:#5e9d7d;color:#9decc4}}.status.fail{{background:#a71230;color:#fff;border-color:#e11}}.status.skip{{color:#ffcb7c}}.arrow{{font-size:24px;color:var(--red)}}
.case-body{{padding:0 23px 24px;display:grid;grid-template-columns:1fr 1fr;gap:15px;border-top:1px solid #3a2e30}}.case-body[hidden]{{display:none}}
.detail{{padding-top:15px}}.detail small{{font-weight:900;font-size:10px;letter-spacing:.15em;color:#fa6777}}.detail p{{margin:7px 0;color:#e9dcd1}}code{{overflow-wrap:anywhere;font-size:12px}}.caution{{grid-column:1/-1;color:var(--muted);font-size:12px;margin:0}}
footer{{margin-top:30px;border-left:5px solid var(--red);padding:15px 20px;background:#180f12;color:#e4c6c0;font-size:12px}}
@media(max-width:680px){{.metrics{{grid-template-columns:1fr 1fr}}.case-head{{grid-template-columns:1fr auto;gap:8px}}.case-index{{grid-column:1/-1}}.case-body{{grid-template-columns:1fr}}header span:last-child{{display:none}}}}
@media(prefers-reduced-motion:no-preference){{.case-head{{transition:background .18s}}.case{{animation:enter .3s ease both}}@keyframes enter{{from{{opacity:.5;translate:0 10px}}to{{opacity:1;translate:0 0}}}}}}
</style></head><body><header><span class="brand">VEILBENCH <b>//</b></span><span>SECURITY ATTACK DEMONSTRATION / OFFLINE EVIDENCE</span></header>
<main><p class="eyebrow">SECURITY TESTING / 09 SCENARIOS</p><h1>ATTACK <em>LAB.</em></h1>
<p class="lead">Real negative-path tests against local FastAPI ASGI applications, temporary SQLite databases and isolated MPyC subprocesses. This report was generated from test results, not simulated browser responses.</p>
<div class="metrics"><div class="metric"><b>{tally}</b><small>SCENARIOS PASSED</small></div>
<div class="metric"><b>{summary['failed']}</b><small>FAILED</small></div><div class="metric"><b>{summary['skipped']}</b><small>NOT RUN / SKIPPED</small></div></div>
<div class="toolbar" role="group" aria-label="Filter scenarios"><button type="button" data-filter="all" aria-pressed="true">ALL</button>
<button type="button" data-filter="PASS" aria-pressed="false">PASS</button>
<button type="button" data-filter="FAIL" aria-pressed="false">FAIL</button>
<button type="button" data-filter="SKIP" aria-pressed="false">NOT RUN</button></div>
<section id="scenarios" aria-label="Attack scenarios">{body}</section>
<footer>RUN: {generated} · SOURCE: CI / LOCAL TESTS ONLY · No private salaries or credentials are captured. Missing-party failure is safe non-completion, not high availability. Demo-host party separation does not imply independent-operator confidentiality.</footer></main>
<script>
document.querySelectorAll('.case-head').forEach(button=>{{
  button.addEventListener('click',()=>{{
    const open=button.getAttribute('aria-expanded')==='true';
    button.setAttribute('aria-expanded', String(!open));
    button.nextElementSibling.hidden=open;
    button.querySelector('.arrow').textContent=open?'+':'−';
  }});
}});
document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{{
  const value=button.dataset.filter;
  document.querySelectorAll('[data-filter]').forEach(x=>x.setAttribute('aria-pressed',String(x===button)));
  document.querySelectorAll('.case').forEach(x=>{{x.hidden=value!=='all' && x.dataset.status!==value}});
}}));
</script></body></html>"""


def run(selected: list[dict], destination: Path) -> int:
    destination.mkdir(parents=True, exist_ok=True)
    xml_path = destination / "pytest-results.xml"
    cmd = [
        sys.executable, "-m", "pytest", *_test_nodes(selected),
        "-q", "-o", "addopts=--asyncio-mode=auto",
        f"--junitxml={xml_path}",
    ]
    print("Executing isolated attack-lab probes (no live HTTP targets)", flush=True)
    try:
        outcome = subprocess.run(
            cmd, check=False, timeout=240,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        rc = outcome.returncode
    except subprocess.TimeoutExpired:
        print("Attack lab timed out; no successful result is claimed", file=sys.stderr)
        rc = 124

    observed = _outcomes(xml_path) if xml_path.exists() else {}
    cases = []
    for case in selected:
        relevant = [case["test"]]
        if case["id"] == "rate-limit":
            relevant = list(THROTTLE_TESTS)
        statuses = [observed.get(name, {}).get("status", "SKIP") for name in relevant]
        status = "FAIL" if "FAIL" in statuses else "PASS" if all(x == "PASS" for x in statuses) else "SKIP"
        cases.append({**case, "status": status, "test_outcomes": statuses})

    report = {
        "report": "VEILBENCH isolated security attack demonstration",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "ASGI/SQLite synthetic accounts and local MPyC subprocesses only; no production service calls",
        "summary": {
            "total": len(cases),
            "passed": sum(c["status"] == "PASS" for c in cases),
            "failed": sum(c["status"] == "FAIL" for c in cases),
            "skipped": sum(c["status"] == "SKIP" for c in cases),
            "pytest_returncode": rc,
            "distinct_test_nodes": len(_test_nodes(selected)),
        },
        "scenarios": cases,
    }
    (destination / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (destination / "index.html").write_text(_render_html(report), encoding="utf-8")
    print("Wrote attack lab evidence:", destination / "report.json", destination / "index.html", flush=True)
    print(json.dumps(report["summary"], indent=2))
    return 0 if rc == 0 and all(item["status"] == "PASS" for item in cases) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List attack scenarios and exit")
    parser.add_argument("--scenario", choices=[c["id"] for c in CASES], help="Run one focused scenario")
    parser.add_argument("--output", default="artifacts/attack-lab", help="Local output directory")
    args = parser.parse_args()
    if args.list:
        for item in CASES:
            print(f"{item['id']:<19} {item['title']}")
        return 0
    selected = [c for c in CASES if not args.scenario or args.scenario == c["id"]]
    return run(selected, Path(args.output))


if __name__ == "__main__":
    raise SystemExit(main())
