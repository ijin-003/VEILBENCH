"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowRight, Check, ChevronRight, CircleAlert, ClipboardCopy,
  LoaderCircle, LockKeyhole, Menu, Play, Plus, RefreshCw,
  ShieldCheck, X,
} from "lucide-react";
import AccountInvite from "./AccountInvite";
import ReactorStage from "./ReactorStage";
import { ProtocolWalkthrough } from "./LearningCenter";

type HealthData = {
  status: string;
  service: string;
  version: string;
  session_storage?: string;
};
type FounderInvite = {
  party_id: number;
  submission_page: string;
  submission_api: string;
  capability_token: string;
};
type SessionData = {
  session_id: string;
  state: string;
  created_at: string;
  expires_at: string;
  submitted_party_ids: number[];
  result?: { aggregate_sum: number; average_salary: number } | null;
  failure_reason?: string | null;
  founder_invites?: FounderInvite[];
};

const apiUrl = (process.env.NEXT_PUBLIC_API_URL || "https://localhost:8000").replace(/\/+$/, "");
const POLL_INTERVAL_MS = 4000;
const FINISHED = new Set(["completed", "failed", "expired"]);
const numberFormat = new Intl.NumberFormat("en-PK", { maximumFractionDigits: 2 });
const PARTY_IDS = [0, 1, 2] as const;

export default function AdminDashboard({ token }: { token: string }) {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [session, setSession] = useState<SessionData | null>(null);
  const [lookupId, setLookupId] = useState("");
  const [busy, setBusy] = useState(false);
  const [computePending, setComputePending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pollWarning, setPollWarning] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [resultOpen, setResultOpen] = useState(true);
  const [copyMessage, setCopyMessage] = useState("");
  const drawerRef = useRef<HTMLElement>(null);
  const drawerButtonRef = useRef<HTMLButtonElement>(null);

  const requestHealth = useCallback(async (signal?: AbortSignal): Promise<HealthData> => {
    const response = await fetch(`${apiUrl}/health`, {
      cache: "no-store", credentials: "omit", referrerPolicy: "no-referrer", signal,
    });
    if (!response.ok) throw new Error(`Backend returned HTTP ${response.status}`);
    return (await response.json()) as HealthData;
  }, []);

  const checkHealth = useCallback(async () => {
    setHealthLoading(true);
    try {
      setHealth(await requestHealth());
      setError(null);
    } catch (cause) {
      setHealth(null);
      setError(cause instanceof Error ? cause.message : "Backend is unreachable");
    } finally {
      setHealthLoading(false);
    }
  }, [requestHealth]);

  useEffect(() => {
    const controller = new AbortController();
    void requestHealth(controller.signal).then((value) => {
      if (!controller.signal.aborted) setHealth(value);
    }).catch((cause: unknown) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Backend is unreachable");
    }).finally(() => {
      if (!controller.signal.aborted) setHealthLoading(false);
    });
    return () => controller.abort();
  }, [requestHealth]);

  const managementRequest = useCallback(async (path: string, method: "GET" | "POST", body?: object): Promise<SessionData> => {
    if (!token) throw new Error("Coordinator authentication required.");
    const response = await fetch(`${apiUrl}/api/v1${path}`, {
      method,
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: body ? JSON.stringify(body) : undefined,
      cache: "no-store", credentials: "omit", referrerPolicy: "no-referrer",
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `Request failed (HTTP ${response.status})`);
    return data as SessionData;
  }, [token]);

  async function createSession(event?: FormEvent) {
    event?.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    setPollWarning(null);
    try {
      const created = await managementRequest("/sessions", "POST", { ttl_minutes: 30 });
      setSession(created);
      setResultOpen(true);
      setDrawerOpen(true); // Invitations are the immediate next step.
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not create session");
    } finally {
      setBusy(false);
    }
  }

  async function loadSession(event: FormEvent) {
    event.preventDefault();
    const sessionId = lookupId.trim();
    if (!sessionId || busy) return;
    setBusy(true);
    setError(null);
    setPollWarning(null);
    try {
      const loaded = await managementRequest(`/sessions/${encodeURIComponent(sessionId)}`, "GET");
      setSession(loaded);
      setResultOpen(true);
      setDrawerOpen(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load session");
    } finally {
      setBusy(false);
    }
  }

  const sessionId = session?.session_id;
  const state = (session?.state || "idle").toLowerCase();

  const refreshSession = useCallback(async () => {
    if (!sessionId || busy) return;
    setBusy(true);
    setError(null);
    try {
      const next = await managementRequest(`/sessions/${encodeURIComponent(sessionId)}`, "GET");
      setSession((current) => current && current.session_id === sessionId
        ? { ...next, founder_invites: current.founder_invites } : current);
      setPollWarning(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not refresh session");
    } finally {
      setBusy(false);
    }
  }, [busy, managementRequest, sessionId]);

  // Only status metadata is polled. Individual salary values never enter this component.
  useEffect(() => {
    if (!sessionId || FINISHED.has(state) || !token) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const next = await managementRequest(`/sessions/${encodeURIComponent(sessionId as string)}`, "GET");
        if (!cancelled) {
          setSession((current) => current && current.session_id === sessionId
            ? { ...next, founder_invites: current.founder_invites } : current);
          setPollWarning(null);
        }
      } catch (cause) {
        if (!cancelled) setPollWarning(cause instanceof Error ? cause.message : "Auto-refresh unavailable");
      } finally {
        if (!cancelled) timer = setTimeout(poll, POLL_INTERVAL_MS);
      }
    }
    timer = setTimeout(poll, POLL_INTERVAL_MS);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [sessionId, state, token, managementRequest]);

  const submitted = new Set(session?.submitted_party_ids ?? []);
  const submittedCount = submitted.size;
  const canCompute = state === "ready" && submittedCount === 3 && !busy && !computePending;
  const isComputing = computePending || state === "computing";
  const complete = state === "completed" && Boolean(session?.result);
  const isConnected = health?.status.toLowerCase() === "ok";
  const fault = state === "failed" || state === "expired";

  async function compute() {
    if (!sessionId || !canCompute) return;
    setBusy(true);
    setComputePending(true);
    setError(null);
    try {
      const next = await managementRequest(`/sessions/${encodeURIComponent(sessionId)}/compute`, "POST");
      setSession((current) => current ? { ...next, founder_invites: current.founder_invites } : next);
      setResultOpen(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Computation could not start");
    } finally {
      setComputePending(false);
      setBusy(false);
    }
  }

  async function copyId() {
    if (!sessionId) return;
    try {
      await navigator.clipboard.writeText(sessionId);
      setCopyMessage("Session ID copied");
    } catch {
      setCopyMessage("Clipboard unavailable — select the session ID to copy it");
    }
  }

  useEffect(() => {
    if (!drawerOpen) return;
    const oldOverflow = document.body.style.overflow;
    const opener = drawerButtonRef.current;
    document.body.style.overflow = "hidden";
    drawerRef.current?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setDrawerOpen(false);
      if (event.key !== "Tab" || !drawerRef.current) return;
      const elements = Array.from(drawerRef.current.querySelectorAll<HTMLElement>(
        'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])',
      )).filter((element) => element.getClientRects().length > 0);
      if (!elements.length) return;
      const first = elements[0];
      const last = elements[elements.length - 1];
      if (event.shiftKey && (document.activeElement === first || document.activeElement === drawerRef.current)) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = oldOverflow;
      window.removeEventListener("keydown", onKey);
      opener?.focus();
    };
  }, [drawerOpen]);

  const headline = complete ? "AGGREGATE COMPLETE" :
    isComputing ? "SECURE COMPUTATION IN PROGRESS" :
    fault ? (state === "expired" ? "SESSION EXPIRED" : "REACTOR ERROR") :
    !session ? "AWAITING INITIALIZATION" :
    state === "ready" && submittedCount === 3 ? "ALL CARTRIDGES DOCKED" :
    `${submittedCount} OF 3 INPUTS SECURED`;

  return (
    <main className={`r4-reactor-root r4-reactor-${state}`}>
      <div className="r4-reactor-layout">
        <header className="r4-reactor-head">
          <div>
            <span className="r4-kicker">THE REACTOR / 03</span>
            <h1>THREE IN. <em>ONE OUT.</em></h1>
          </div>
          <div className="r4-reactor-actions">
            <span className={`r4-link ${isConnected ? "r4-link--online" : ""}`} role="status">
              <i />{healthLoading ? "CONNECTING" : isConnected ? "LINK ACTIVE" : "LINK UNVERIFIED"}
            </span>
            <button ref={drawerButtonRef} className="r4-tools" type="button" onClick={() => setDrawerOpen(true)} aria-controls="ch-drawer" aria-expanded={drawerOpen}>
              <Menu size={18} aria-hidden="true" /> SESSION TOOLS
            </button>
          </div>
        </header>

        <section className="r4-reactor-view" aria-label="Three-founder computation chamber">
          <ReactorStage submitted={submitted} stage={isComputing ? "computing" : state} />
        </section>

        <div className="r4-reactor-command">
          <div className="r4-reactor-status" role="status" aria-live="polite">
            <span className="r4-status-eyebrow">LIVE PROTOCOL STATUS</span>
            <strong>{headline}</strong>
          </div>
          <div className="r4-command-buttons">
            {session && <button type="button" className="r4-refresh" onClick={() => void refreshSession()} disabled={busy} aria-label="Refresh submission status" title="Refresh"><RefreshCw size={19} aria-hidden="true"/></button>}
            {!session ? (
              <button type="button" className="r4-primary" disabled={busy} onClick={() => void createSession()}>{busy ? <LoaderCircle size={18} className="ch-spin"/> : <Plus size={18}/>} CREATE SESSION <ArrowRight size={18}/></button>
            ) : canCompute ? (
              <button type="button" className="r4-primary" onClick={() => void compute()}><Play size={17}/> ENGAGE COMPUTATION <ArrowRight size={18}/></button>
            ) : complete ? (
              <button type="button" className="r4-primary r4-primary--light" onClick={() => setResultOpen(value => !value)}><Check size={17}/>{resultOpen ? "HIDE RESULT" : "REVEAL RESULT"}<ChevronRight size={18}/></button>
            ) : fault ? (
              <button type="button" className="r4-primary" onClick={() => setDrawerOpen(true)}><CircleAlert size={17}/> SESSION OPTIONS <ArrowRight size={18}/></button>
            ) : (
              <button type="button" className="r4-primary" disabled><LockKeyhole size={17}/>{isComputing ? "COMPUTING…" : "AWAITING THREE INPUTS"}</button>
            )}
          </div>
        </div>

        {complete && resultOpen && session?.result && (
          <section className="r4-results" aria-label="Computed aggregate results" aria-live="polite">
            <span className="r4-results-mark">AGGREGATE / RELEASED</span>
            <div><small>SUM</small><strong>{numberFormat.format(session.result.aggregate_sum)}</strong></div>
            <div><small>AVERAGE</small><strong>{numberFormat.format(session.result.average_salary)}</strong></div>
          </section>
        )}

        {(error || pollWarning || session?.failure_reason) && <div className="r4-alerts">
          {error && <p role="alert">{error}</p>}
          {session?.failure_reason && <p role="alert">{session.failure_reason}</p>}
          {pollWarning && <p role="status">Sync warning: {pollWarning}</p>}
        </div>}
        <p className="r4-privacy"><ShieldCheck size={14} aria-hidden="true"/> Submission status only. Individual salaries never appear in this interface.</p>
      </div>

      {drawerOpen && <div className="ch-drawer-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setDrawerOpen(false); }}>
        <section className="ch-drawer" id="ch-drawer" ref={drawerRef} role="dialog" aria-modal="true" aria-label="Session management tools" tabIndex={-1}>
          <header className="ch-drawer-head"><div><small>VEILBENCH / ADMIN</small><h2>SESSION <em>TOOLS.</em></h2></div><button type="button" onClick={() => setDrawerOpen(false)} aria-label="Close session tools"><X size={22}/></button></header>
          <div className="ch-drawer-scroll">
            <section className="ch-tool-section">
              <div className="ch-tool-heading"><span>01</span><h3>MANAGE SESSION</h3></div>
              <button type="button" className="ch-drawer-action" onClick={() => void createSession()} disabled={busy}><Plus size={16}/> CREATE NEW 30-MIN SESSION</button>
              <form onSubmit={loadSession} className="ch-load-form"><label htmlFor="ch-session-id-lookup">LOAD EXISTING SESSION</label><div><input id="ch-session-id-lookup" value={lookupId} onChange={(event) => setLookupId(event.target.value)} placeholder="Session ID" autoComplete="off"/><button type="submit" aria-label="Load session" disabled={!lookupId.trim() || busy}><ArrowRight size={17}/></button></div></form>
              {session && <div className="ch-session-meta"><small>CURRENT SESSION</small><div><code>{session.session_id}</code><button type="button" onClick={() => void copyId()} aria-label="Copy session ID"><ClipboardCopy size={16}/></button></div><small>EXPIRES: {new Date(session.expires_at).toLocaleString()}</small><small>STATE: {session.state.toUpperCase()}</small>{copyMessage && <p role="status">{copyMessage}</p>}</div>}
            </section>
            <section className="ch-tool-section">
              <div className="ch-tool-heading"><span>02</span><h3>CONNECTION</h3></div>
              <p>{health ? `${health.service} · v${health.version}` : "Backend connection not verified"}</p><p>Storage: {health?.session_storage || "unknown"}</p>
              <button type="button" className="ch-drawer-action ch-drawer-action--subtle" onClick={() => void checkHealth()} disabled={healthLoading}><RefreshCw size={16}/> RECHECK CONNECTION</button>
            </section>
            {session && !FINISHED.has(state) && <section className="ch-tool-section">
              <div className="ch-tool-heading"><span>03</span><h3>PRIVATE INVITATIONS</h3></div>
              <p>Issue one separate account invitation per founder. Send credentials privately, never in a public channel.</p>
              {PARTY_IDS.map((partyId) => <div key={`${session.session_id}-${partyId}`} className="ch-invite-card"><h4>FOUNDER 0{partyId + 1}</h4><AccountInvite token={token} sessionId={session.session_id} partyId={partyId}/></div>)}
            </section>}
            <section className="ch-tool-section">
              <div className="ch-tool-heading"><span>04</span><h3>PROTOCOL EXPLAINER</h3></div>
              <details className="ch-drawer-guide"><summary>HOW THE THREE-PARTY COMPUTATION WORKS</summary><div><ProtocolWalkthrough /></div></details>
            </section>
          </div>
          <div className="ch-drawer-foot"><span><LockKeyhole size={13}/> INDIVIDUAL SALARIES NEVER DISPLAYED</span></div>
        </section>
      </div>}
    </main>
  );
}
