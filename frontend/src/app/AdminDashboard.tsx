"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  CheckCircle2,
  Copy,
  ExternalLink,
  Play,
  Plus,
  RefreshCw,
  Server,
  ShieldCheck,
  Users,
  ArrowUpRight,
  Activity,
  RadioTower,
  Terminal,
  Clock3,
  RotateCcw,
} from "lucide-react";
import AccountInvite from "./AccountInvite";

interface HealthData {
  status: string;
  service: string;
  version: string;
  session_storage?: string;
  mpc_configuration?: { parties: number; threshold: number; honest_majority: boolean };
}

interface FounderInvite {
  party_id: number;
  submission_page: string;
  submission_api: string;
  capability_token: string;
}

interface SessionData {
  session_id: string;
  state: string;
  created_at: string;
  expires_at: string;
  submitted_party_ids: number[];
  result?: { aggregate_sum: number; average_salary: number } | null;
  failure_reason?: string | null;
  founder_invites?: FounderInvite[];
}

const apiUrl = (process.env.NEXT_PUBLIC_API_URL || "https://localhost:8000").replace(/\/+$/, "");
const POLL_INTERVAL_MS = 4_000;
const TERMINAL_STATES = new Set(["completed", "failed", "expired"]);
const numberFormat = new Intl.NumberFormat("en-PK", { maximumFractionDigits: 2 });

export default function AdminDashboard({ token }: { token: string }) {
  const [health, setHealth] = useState<HealthData | null>(null);
  const adminToken = token;
  const [sessionLookupId, setSessionLookupId] = useState("");
  const [session, setSession] = useState<SessionData | null>(null);
  const [loading, setLoading] = useState(false);
  const [healthLoading, setHealthLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pollWarning, setPollWarning] = useState<string | null>(null);
  const [copyNotice, setCopyNotice] = useState<string | null>(null);

  const requestHealth = useCallback(async (signal?: AbortSignal): Promise<HealthData> => {
    const response = await fetch(`${apiUrl}/health`, {
      cache: "no-store",
      credentials: "omit",
      referrerPolicy: "no-referrer",
      signal,
    });
    if (!response.ok) throw new Error(`Backend returned HTTP ${response.status}`);
    return (await response.json()) as HealthData;
  }, []);

  const checkHealth = useCallback(async () => {
    setHealthLoading(true);
    try {
      setHealth(await requestHealth());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not reach the backend");
    } finally {
      setHealthLoading(false);
    }
  }, [requestHealth]);

  useEffect(() => {
    const controller = new AbortController();

    void requestHealth(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setHealth(data);
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) {
          setError(cause instanceof Error ? cause.message : "Could not reach the backend");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setHealthLoading(false);
      });

    return () => controller.abort();
  }, [requestHealth]);

  const managementRequest = useCallback(
    async (path: string, method: "GET" | "POST", body?: object) => {
      if (!adminToken) throw new Error("Enter the coordinator management token first.");
      const response = await fetch(`${apiUrl}/api/v1${path}`, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${adminToken}`,
        },
        body: body ? JSON.stringify(body) : undefined,
        cache: "no-store",
        credentials: "omit",
        referrerPolicy: "no-referrer",
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || `Request failed with HTTP ${response.status}`);
      }
      return data as SessionData;
    },
    [adminToken],
  );

  async function createSession(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setPollWarning(null);
    setSession(null);
    try {
      const created = await managementRequest("/sessions", "POST", { ttl_minutes: 30 });
      setSession(created);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not create the session");
    } finally {
      setLoading(false);
    }
  }

  async function loadExistingSession(event: FormEvent) {
    event.preventDefault();
    const sessionId = sessionLookupId.trim();
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    setPollWarning(null);
    try {
      const loaded = await managementRequest(`/sessions/${encodeURIComponent(sessionId)}`, "GET");
      setSession(loaded);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load the session");
    } finally {
      setLoading(false);
    }
  }

  const refreshSession = useCallback(async () => {
    if (!session) return;
    setLoading(true);
    setError(null);
    try {
      const next = await managementRequest(`/sessions/${session.session_id}`, "GET");
      setSession((current) =>
        current ? { ...next, founder_invites: current.founder_invites } : current,
      );
      setPollWarning(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not refresh the session");
    } finally {
      setLoading(false);
    }
  }, [managementRequest, session]);

  const activeSessionId = session?.session_id;
  const activeSessionState = session?.state.toLowerCase();

  // Poll only the metadata endpoint. No founder salary is sent to this page or coordinator.
  useEffect(() => {
    const sessionId = activeSessionId;
    if (!sessionId || !activeSessionState || TERMINAL_STATES.has(activeSessionState) || !adminToken) return;

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    const poll = async () => {
      try {
        const next = await managementRequest(`/sessions/${sessionId}`, "GET");
        if (!cancelled) {
          setSession((current) =>
            current && current.session_id === sessionId
              ? { ...next, founder_invites: current.founder_invites }
              : current,
          );
          setPollWarning(null);
        }
      } catch (cause) {
        if (!cancelled) {
          setPollWarning(
            cause instanceof Error ? cause.message : "Automatic status refresh is temporarily unavailable.",
          );
        }
      } finally {
        if (!cancelled) timer = setTimeout(poll, POLL_INTERVAL_MS);
      }
    };

    timer = setTimeout(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [activeSessionId, activeSessionState, adminToken, managementRequest]);

  async function computeSession() {
    if (!session || session.state.toLowerCase() !== "ready" || session.submitted_party_ids.length !== 3) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const next = await managementRequest(`/sessions/${session.session_id}/compute`, "POST");
      setSession({ ...next, founder_invites: session.founder_invites });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Computation could not start");
    } finally {
      setLoading(false);
    }
  }

  async function copyValue(value: string, label: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopyNotice(`${label} copied.`);
      window.setTimeout(() => setCopyNotice(null), 2500);
    } catch {
      setCopyNotice("Clipboard access is unavailable. Copy the value from its link instead.");
    }
  }

  const submitted = new Set(session?.submitted_party_ids ?? []);
  const canCompute = Boolean(
    session && session.state.toLowerCase() === "ready" && session.submitted_party_ids.length === 3,
  );

  const status = session?.state.toLowerCase() || "standby";
  const isConnected = Boolean(health && health.status.toLowerCase() === "ok");
  const submittedCount = session?.submitted_party_ids.length ?? 0;
  const progress = Math.min(100, Math.round((submittedCount / 3) * 100));

  return (
    <main className="mc-root">
      <div className="mc-background-grid" aria-hidden="true" />
      <div className="mc-shell">
        <header className="mc-topline">
          <div className="mc-identity">
            <span className="mc-emblem" aria-hidden="true">V<span>◆</span></span>
            <div>
              <span className="mc-brand">VEILBENCH</span>
              <span className="mc-brand-sub">OPERATIONS / COORDINATOR</span>
            </div>
          </div>
          <div className="mc-top-right">
            <span className="mc-environment"><span className={`mc-dot ${isConnected ? "mc-dot-live" : ""}`} /> {healthLoading ? "CONNECTING" : isConnected ? "SYSTEM ONLINE" : "STATUS UNAVAILABLE"}</span>
            <span className="mc-top-index">CONTROL DECK — 01</span>
          </div>
        </header>

        <div className="mc-headline-row">
          <div>
            <div className="mc-eyebrow"><span className="mc-rule" /> LIVE OPERATIONS / PRIVATE BENCHMARK</div>
            <h1 className="mc-title">MISSION <em>CONTROL.</em></h1>
            <p className="mc-intro">Three private inputs. One collective result. All the coordination you need, nothing you shouldn’t see.</p>
          </div>
          <div className="mc-system-flag" aria-hidden="true"><span>03</span><small>PARTY<br/>PROTOCOL</small></div>
        </div>

        <div className="mc-command-grid">
          <section className="mc-radar-panel" aria-labelledby="mc-radar-heading">
            <div className="mc-panel-top">
              <span className="mc-panel-label"><Activity size={15} /> LIVE SESSION MONITOR</span>
              <span className="mc-panel-code">MON / 001</span>
            </div>
            <div className="mc-radar-wrap">
              <svg className="mc-radar" viewBox="0 0 460 320" role="img" aria-label={`Three party signal monitor: ${submittedCount} of 3 submissions received`}>
                <defs>
                  <linearGradient id="mc-scan" x1="0" x2="1"><stop offset="0" stopColor="#f53b44" stopOpacity="0" /><stop offset="1" stopColor="#f53b44" stopOpacity=".32" /></linearGradient>
                </defs>
                <g className="mc-radar-center" transform="translate(230 161)">
                  {[45,76,111,145].map(r => <circle key={r} r={r} fill="none" stroke="#f2e6d3" strokeOpacity={r===145?".14":".1"} strokeWidth="1" strokeDasharray={r===145?"3 8":"none"} />)}
                  <path d="M-160 0H160M0 -154V154" stroke="#f2e6d3" strokeOpacity=".11" />
                  <path d="M0 0 L0 -145 A145 145 0 0 1 145 0 Z" fill="url(#mc-scan)" className="mc-radar-sweep" />
                  {([[-104,65],[0,-110],[104,65]] as const).map(([x,y],i) => {
                    const received = submitted.has(i);
                    return <g key={i} transform={`translate(${x} ${y})`}>
                      <circle r="26" fill={received?"#ef2538":"#171519"} stroke={received?"#ef2538":"#6b5f60"} strokeWidth="2" />
                      <circle r="32" fill="none" stroke={received?"#ef2538":"#8f8280"} strokeOpacity=".42" strokeDasharray="3 5" className={received ? "mc-radar-pulse" : ""}/>
                      <text y="6" textAnchor="middle" fill={received?"#fff":"#d9cbc2"} fontSize="17" fontWeight="900">{String(i+1).padStart(2,"0")}</text>
                    </g>;
                  })}
                  <circle r="9" fill="#f3e9dd" />
                  <circle r="3" fill="#e50922" />
                </g>
              </svg>
              <div className="mc-radar-center-copy"><strong>{submittedCount}<span>/03</span></strong><small>SIGNALS RECEIVED</small></div>
            </div>
            <div className="mc-radar-footer">
              <span><span className="mc-live-pulse" /> AUTO-SYNC / 4 SEC</span>
              <span>{session ? `SESSION ${session.session_id.slice(0,8).toUpperCase()}` : "AWAITING SESSION"}</span>
            </div>
          </section>

          <div className="mc-right-column">
            <section className="mc-status-panel" aria-labelledby="mc-status-heading">
              <div className="mc-panel-top"><span className="mc-panel-label"><RadioTower size={15} /> NETWORK STATUS</span><span className="mc-panel-code">SYS / 002</span></div>
              <div className="mc-status-main">
                <div><span className="mc-small-label" id="mc-status-heading">COORDINATOR LINK</span><strong>{healthLoading ? "CHECKING" : health ? health.status.toUpperCase() : "UNAVAILABLE"}</strong><small>{health ? `${health.service} · v${health.version}` : "Connection not verified"}</small></div>
                <div className={`mc-status-symbol ${isConnected?"mc-status-symbol-live":""}`} aria-hidden="true"><Server size={34}/></div>
              </div>
              <div className="mc-status-footer"><span>STORAGE / {health?.session_storage || "UNKNOWN"}</span><button type="button" onClick={() => void checkHealth()} disabled={healthLoading}><RefreshCw size={14}/> RECHECK</button></div>
            </section>

            <section className="mc-operations" aria-labelledby="mc-ops-heading">
              <div className="mc-panel-top"><span className="mc-panel-label"><Terminal size={15}/> SESSION COMMANDS</span><span className="mc-panel-code">OPS / 003</span></div>
              <h2 id="mc-ops-heading">INITIATE <em>BENCHMARK</em></h2>
              <p>Start a new three-party round or retrieve an existing session.</p>
              <form onSubmit={createSession}>
                <button className="mc-command-primary" type="submit" disabled={loading || !adminToken.trim()}><Plus size={19}/> CREATE 30-MIN SESSION <ArrowUpRight size={18}/></button>
              </form>
              <form className="mc-retrieve" onSubmit={loadExistingSession}>
                <label htmlFor="mc-session-lookup">RETRIEVE EXISTING SESSION</label>
                <div className="mc-retrieve-row"><input id="mc-session-lookup" type="text" autoComplete="off" placeholder="Paste session ID" value={sessionLookupId} onChange={event => setSessionLookupId(event.target.value)} /><button type="submit" disabled={loading || !adminToken.trim() || !sessionLookupId.trim()} aria-label="Load existing session"><ArrowUpRight size={20}/></button></div>
              </form>
            </section>
          </div>
        </div>

        {error && <p role="alert" className="mc-alert">{error}</p>}
        {pollWarning && <p role="status" className="mc-warning">Status refresh warning: {pollWarning}</p>}

        <section className="mc-flow" aria-labelledby="mc-flow-heading">
          <div className="mc-flow-header"><div><span className="mc-eyebrow">OPERATION / 02</span><h2 id="mc-flow-heading">THE <em>PROTOCOL.</em></h2></div><span className="mc-flow-caption">SECURE MULTIPARTY COMPUTATION</span></div>
          <div className="mc-flow-steps">
            <div className="mc-flow-step"><span className="mc-step-number">01</span><strong>INITIALIZE</strong><small>{session ? "SESSION CREATED" : "AWAITING LAUNCH"}</small></div>
            <span className="mc-flow-connector" aria-hidden="true" />
            <div className="mc-flow-step"><span className="mc-step-number">02</span><strong>COLLECT</strong><small>{submittedCount} OF 3 RECEIVED</small></div>
            <span className="mc-flow-connector" aria-hidden="true" />
            <div className="mc-flow-step"><span className="mc-step-number">03</span><strong>COMPUTE</strong><small>{session?.result ? "COMPLETE" : status === "computing" ? "IN PROGRESS" : "PENDING"}</small></div>
          </div>
          <div className="mc-progress-track" role="progressbar" aria-valuemin={0} aria-valuemax={3} aria-valuenow={submittedCount} aria-label="Founder submissions received"><span style={{width:`${progress}%`}}/></div>
        </section>

        {session && <section className="mc-active" aria-labelledby="mc-active-heading">
          <div className="mc-section-title"><div><span className="mc-eyebrow">ACTIVE OPERATION / 03</span><h2 id="mc-active-heading">SESSION <em>DETAILS.</em></h2></div><span className={`mc-state mc-state-${status}`}>{session.state}</span></div>
          <div className="mc-session-bar"><div><span className="mc-small-label">SESSION IDENTIFIER</span><code>{session.session_id}</code></div><div><span className="mc-small-label">EXPIRATION</span><span><Clock3 size={14}/> {new Date(session.expires_at).toLocaleString()}</span></div></div>
          <div className="mc-party-grid">
            {[0,1,2].map(partyId => <div className={`mc-party ${submitted.has(partyId)?"mc-party-ready":""}`} key={partyId}><span className="mc-party-index">0{partyId+1}</span><div><strong>FOUNDER {partyId+1}</strong><span>{submitted.has(partyId)?"INPUT RECEIVED":"AWAITING INPUT"}</span></div>{submitted.has(partyId)?<CheckCircle2 size={23}/>:<span className="mc-waiting-ring"/>}</div>)}
          </div>
          <div className="mc-session-actions"><button type="button" className="mc-action-secondary" onClick={() => void refreshSession()} disabled={loading}><RotateCcw size={16}/> CHECK STATUS</button><button type="button" className="mc-action-compute" onClick={() => void computeSession()} disabled={loading || !canCompute}><Play size={17}/> COMPUTE AGGREGATE <ArrowUpRight size={18}/></button></div>
          <p className="mc-note">Individual salaries are never shown in this dashboard. Computation becomes available after all three submissions are confirmed.</p>

          {session.founder_invites && status !== "completed" && <div className="mc-invites"><div className="mc-invite-heading"><span className="mc-eyebrow">SECURE DISTRIBUTION / 04</span><h3>PRIVATE INVITATIONS</h3><p>Share each account invitation privately. Participants activate their account and choose a password before signing in.</p></div><div className="mc-invite-grid">{session.founder_invites.map(invite => <article key={invite.party_id} className="mc-invite"><div className="mc-invite-label"><Users size={17}/> FOUNDER {invite.party_id+1}</div><a href="/" target="_blank" rel="noreferrer">OPEN SIGN-IN <ExternalLink size={14}/></a><button type="button" className="mc-action-secondary" onClick={() => void copyValue(window.location.origin, `Founder ${invite.party_id+1} sign-in link`)}><Copy size={15}/> COPY LINK</button><AccountInvite key={`${session.session_id}-${invite.party_id}`} token={token} sessionId={session.session_id} partyId={invite.party_id}/></article>)}</div>{copyNotice && <p role="status" className="mc-copy-notice">{copyNotice}</p>}</div>}
          {session.result && <section className="mc-results" aria-labelledby="mc-result-title"><span className="mc-eyebrow">COMPUTATION COMPLETE / FINAL REVEAL</span><h3 id="mc-result-title">COLLECTIVE <em>INSIGHT.</em></h3><div className="mc-result-grid"><div><span>AGGREGATE SALARY</span><strong>{numberFormat.format(session.result.aggregate_sum)}</strong></div><div><span>AVERAGE SALARY</span><strong>{numberFormat.format(session.result.average_salary)}</strong></div></div><p>Aggregate statistics only. No individual salary values are disclosed here.</p></section>}
          {session.failure_reason && <p role="alert" className="mc-alert">{session.failure_reason}</p>}
        </section>}
        <footer className="mc-footer"><span>VEILBENCH / MISSION CONTROL</span><span>SECURE SESSION MANAGEMENT · THREE-PARTY MPC</span><ShieldCheck size={17}/></footer>
      </div>
    </main>
  );
}
