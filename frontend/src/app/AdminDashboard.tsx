"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowRight, ClipboardCopy, LockKeyhole, Plus, RefreshCw, X,
} from "lucide-react";
import AccountInvite from "./AccountInvite";
import { OperationsReactor, OperationsResults } from "./OperationsScreens";
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

type AccountRecord = {
  username: string;
  display_name?: string | null;
  role: string;
  created_at: string | null;
  activation_status: "active" | "invited" | "expired";
  benchmark_id: string | null;
  party_id: number | null;
  invitation_expiry: number | null;
};
type AccountDirectory = { accounts: AccountRecord[]; total: number };
type SessionDirectory = { sessions: SessionData[]; total: number };
const DIRECTORY_PAGE_SIZE = 30;
function remainingTime(expiry: string, clockMs: number): string {
  const seconds = Math.max(0, Math.ceil((Date.parse(expiry) - clockMs) / 1000));
  if (!Number.isFinite(seconds) || seconds <= 0) return "EXPIRED";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const tail = String(seconds % 60).padStart(2, "0");
  return hours ? `${hours}h ${String(minutes).padStart(2, "0")}m ${tail}s` : `${minutes}m ${tail}s`;
}

const apiUrl = (process.env.NEXT_PUBLIC_API_URL || "https://localhost:8000").replace(/\/+$/, "");
const POLL_INTERVAL_MS = 4000;
const FINISHED = new Set(["completed", "failed", "expired"]);
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
  const [accountDirectory, setAccountDirectory] = useState<AccountDirectory | null>(null);
  const [sessionDirectory, setSessionDirectory] = useState<SessionDirectory | null>(null);
  const [directoryError, setDirectoryError] = useState<string | null>(null);
  const [directoryBusy, setDirectoryBusy] = useState(false);
  const [accountOffset, setAccountOffset] = useState(0);
  const [sessionOffset, setSessionOffset] = useState(0);
  const [sessionScope, setSessionScope] = useState<"active" | "all">("active");
  const [clockMs, setClockMs] = useState(() => Date.now());
  const [copyMessage, setCopyMessage] = useState("");
  const drawerRef = useRef<HTMLElement>(null);
  const drawerButtonRef = useRef<HTMLButtonElement>(null);
  const directorySeqRef = useRef(0);

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

  const directoryRequest = useCallback(async (path: string): Promise<unknown> => {
    const response = await fetch(`${apiUrl}/api/v1${path}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store", credentials: "omit", referrerPolicy: "no-referrer",
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `Directory request failed (HTTP ${response.status})`);
    return data;
  }, [token]);

  const refreshDirectories = useCallback(async () => {
    const seq = ++directorySeqRef.current;
    setDirectoryBusy(true);
    try {
      const [accounts, sessions] = await Promise.all([
        directoryRequest(`/accounts?limit=${DIRECTORY_PAGE_SIZE}&offset=${accountOffset}`),
        directoryRequest(`/sessions?scope=${sessionScope}&limit=${DIRECTORY_PAGE_SIZE}&offset=${sessionOffset}`),
      ]);
      if (seq !== directorySeqRef.current) return;
      setAccountDirectory(accounts as AccountDirectory);
      setSessionDirectory(sessions as SessionDirectory);
      setDirectoryError(null);
    } catch (cause) {
      if (seq !== directorySeqRef.current) return;
      setDirectoryError(cause instanceof Error ? cause.message : "Could not load account/session directories");
    } finally {
      if (seq === directorySeqRef.current) {
        setDirectoryBusy(false);
      }
    }
  }, [directoryRequest, accountOffset, sessionOffset, sessionScope]);

  useEffect(() => {
    if (!drawerOpen) return;
    const initial = setTimeout(() => { void refreshDirectories(); }, 0);
    const timer = setInterval(() => { setClockMs(Date.now()); }, 1000);
    const refresh = setInterval(() => { void refreshDirectories(); }, 15000);
    return () => { clearTimeout(initial); clearInterval(timer); clearInterval(refresh); };
  }, [drawerOpen, refreshDirectories]);

  async function openListedSession(id: string) {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const opened = await managementRequest(`/sessions/${encodeURIComponent(id)}`, "GET");
      setSession((current) => ({ ...opened,
        founder_invites: current?.session_id === id ? current.founder_invites : undefined }));
      setResultOpen(true);
      setPollWarning(null);
      setDrawerOpen(false);
    } catch (cause) {
      setDirectoryError(cause instanceof Error ? cause.message : "Could not open session");
    } finally {
      setBusy(false);
    }
  }

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
  const isConnected = health?.status.toLowerCase() === "healthy" || health?.status.toLowerCase() === "ok";
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

  async function recoverSession() {
    if (!sessionId || busy) return;
    setBusy(true);
    setError(null);
    try {
      const next = await managementRequest(`/sessions/${encodeURIComponent(sessionId)}/recover`, "POST");
      setSession((current) => current ? { ...next, founder_invites: current.founder_invites } : next);
      void refreshDirectories();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Recovery failed");
    } finally {
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
    <main className={`vb-ops r4-reactor-root r4-reactor-${state}`}>
      {complete && resultOpen && session?.result ? (
        <OperationsResults sum={session.result.aggregate_sum} average={session.result.average_salary} onBack={() => setResultOpen(false)}/>
      ) : (
        <OperationsReactor
          submitted={submitted} state={state} connected={isConnected} connecting={healthLoading}
          headline={headline} busy={busy} computing={isComputing} hasSession={Boolean(session)}
          canCompute={canCompute} complete={complete}
          onTools={() => setDrawerOpen(true)} onCreate={() => void createSession()}
          onRefresh={() => void refreshSession()} onCompute={() => void compute()}
          onReveal={() => setResultOpen(true)}
        />
      )}
      {(error || pollWarning || session?.failure_reason) && <div className="ops-live-warning">
        {error && <p role="alert">{error}</p>}
        {session?.failure_reason && <p role="alert">{session.failure_reason}</p>}
        {pollWarning && <p role="status">Sync warning: {pollWarning}</p>}
      </div>}
      {drawerOpen && <div className="ch-drawer-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setDrawerOpen(false); }}>
        <section className="ch-drawer" id="ch-drawer" ref={drawerRef} role="dialog" aria-modal="true" aria-label="Session management tools" tabIndex={-1}>
          <header className="ch-drawer-head"><div><small>VEILBENCH / ADMIN</small><h2>SESSION <em>TOOLS.</em></h2></div><button type="button" onClick={() => setDrawerOpen(false)} aria-label="Close session tools"><X size={22}/></button></header>
          <div className="ch-drawer-scroll">
            <section className="ch-tool-section">
              <div className="ch-tool-heading"><span>01</span><h3>MANAGE SESSION</h3></div>
              <button type="button" className="ch-drawer-action" onClick={() => void createSession()} disabled={busy}><Plus size={16}/> CREATE NEW 30-MIN SESSION</button>
              <form onSubmit={loadSession} className="ch-load-form"><label htmlFor="ch-session-id-lookup">LOAD EXISTING SESSION</label><div><input id="ch-session-id-lookup" value={lookupId} onChange={(event) => setLookupId(event.target.value)} placeholder="Session ID" autoComplete="off"/><button type="submit" aria-label="Load session" disabled={!lookupId.trim() || busy}><ArrowRight size={17}/></button></div></form>
              {session && <div className="ch-session-meta"><small>CURRENT SESSION</small><div><code>{session.session_id}</code><button type="button" onClick={() => void copyId()} aria-label="Copy session ID"><ClipboardCopy size={16}/></button></div><small>EXPIRES: {new Date(session.expires_at).toLocaleString()}</small><small>STATE: {session.state.toUpperCase()}</small>{state === "computing" && <button type="button" className="ch-drawer-action ch-drawer-action--subtle" disabled={busy} onClick={() => void recoverSession()}>RECOVER STUCK SESSION</button>}{copyMessage && <p role="status">{copyMessage}</p>}</div>}
            </section>
            <section className="ch-tool-section" aria-label="Session directory">
              <div className="ch-tool-heading"><span>02</span><h3>SESSION DIRECTORY</h3></div>
              <div className="ch-directory-controls">
                <button type="button" aria-pressed={sessionScope === "active"} className={sessionScope === "active" ? "is-active" : ""} onClick={() => { setSessionOffset(0); setSessionScope("active"); }}>ACTIVE</button>
                <button type="button" aria-pressed={sessionScope === "all"} className={sessionScope === "all" ? "is-active" : ""} onClick={() => { setSessionOffset(0); setSessionScope("all"); }}>HISTORY</button>
                <button type="button" aria-label="Refresh directories" onClick={() => void refreshDirectories()} disabled={directoryBusy}><RefreshCw size={14} /></button>
              </div>
              <p>Session timers update live. Select a session to see its latest founder-submission status.</p>
              <div className="ch-directory-list" role="list" aria-label="Benchmark sessions">
                {sessionDirectory?.sessions.map((item) => (
                  <div className="ch-directory-entry" key={item.session_id} role="listitem">
                    <div className="ch-directory-entry-top"><strong>{item.state.toUpperCase()}</strong>
                      {item.state.toLowerCase() === "completed" || item.state.toLowerCase() === "failed" ? (
                        <span className="ch-directory-clock">CLOSED</span>
                      ) : (
                        <time dateTime={item.expires_at} className="ch-directory-clock">{remainingTime(item.expires_at, clockMs)}</time>
                      )}</div>
                    <code title={item.session_id}>{item.session_id}</code>
                    <small>{item.submitted_party_ids.length} / 3 submissions · Created {new Date(item.created_at).toLocaleString()}</small>
                    <button type="button" disabled={busy} onClick={() => void openListedSession(item.session_id)}>OPEN SESSION <ArrowRight size={14}/></button>
                  </div>
                ))}
                {sessionDirectory && sessionDirectory.sessions.length === 0 && <p>No {sessionScope === "active" ? "active" : "recorded"} sessions.</p>}
                {!sessionDirectory && !directoryError && <p>Loading sessions…</p>}
              </div>
              {sessionDirectory && <div className="ch-directory-pages">
                <span>{sessionDirectory.total} total · {(sessionDirectory.total ? sessionOffset + 1 : 0)}–{Math.min(sessionOffset + DIRECTORY_PAGE_SIZE, sessionDirectory.total)}</span>
                <button type="button" onClick={() => setSessionOffset(Math.max(0, sessionOffset - DIRECTORY_PAGE_SIZE))} disabled={sessionOffset === 0}>PREV</button>
                <button type="button" onClick={() => setSessionOffset(sessionOffset + DIRECTORY_PAGE_SIZE)} disabled={sessionOffset + DIRECTORY_PAGE_SIZE >= sessionDirectory.total}>NEXT</button>
              </div>}
            </section>
            <section className="ch-tool-section" aria-label="Registered account directory">
              <div className="ch-tool-heading"><span>03</span><h3>ACCOUNT DIRECTORY</h3></div>
              <p>All invited and activated accounts; no passwords, invitation tokens, or private salary values.</p>
              <div className="ch-directory-list" role="list" aria-label="Registered and invited users">
                {accountDirectory?.accounts.map((item) => (
                  <div className="ch-directory-entry ch-account-entry" role="listitem" key={item.username}>
                    <div className="ch-directory-entry-top"><strong>{item.display_name || item.username}</strong><span className="ch-directory-account-status">{item.activation_status.toUpperCase()}</span></div>
                    <small>{item.display_name ? `${item.username} · ` : ""}{item.role.toUpperCase()} {item.party_id !== null ? `· FOUNDER ${item.party_id + 1}` : ""}</small>
                    <small>Invitation created: {item.created_at ? new Date(item.created_at).toLocaleString() : "Not recorded (legacy account)"}</small>
                    {item.benchmark_id && <code title={item.benchmark_id}>Session: {item.benchmark_id}</code>}
                  </div>
                ))}
                {accountDirectory && accountDirectory.accounts.length === 0 && <p>No accounts found.</p>}
                {!accountDirectory && !directoryError && <p>Loading accounts…</p>}
              </div>
              {accountDirectory && <div className="ch-directory-pages">
                <span>{accountDirectory.total} accounts</span>
                <button type="button" onClick={() => setAccountOffset(Math.max(0, accountOffset - DIRECTORY_PAGE_SIZE))} disabled={accountOffset === 0}>PREV</button>
                <button type="button" onClick={() => setAccountOffset(accountOffset + DIRECTORY_PAGE_SIZE)} disabled={accountOffset + DIRECTORY_PAGE_SIZE >= accountDirectory.total}>NEXT</button>
              </div>}
              {directoryError && <p role="alert" className="ch-directory-error">{directoryError}</p>}
            </section>
            <section className="ch-tool-section">
              <div className="ch-tool-heading"><span>04</span><h3>CONNECTION</h3></div>
              <p>{health ? `${health.service} · v${health.version}` : "Backend connection not verified"}</p><p>Storage: {health?.session_storage || "unknown"}</p>
              <button type="button" className="ch-drawer-action ch-drawer-action--subtle" onClick={() => void checkHealth()} disabled={healthLoading}><RefreshCw size={16}/> RECHECK CONNECTION</button>
            </section>
            {session && !FINISHED.has(state) && <section className="ch-tool-section">
              <div className="ch-tool-heading"><span>05</span><h3>PRIVATE INVITATIONS</h3></div>
              <p>Issue one separate account invitation per founder. Send credentials privately, never in a public channel.</p>
              {PARTY_IDS.map((partyId) => <div key={`${session.session_id}-${partyId}`} className="ch-invite-card"><h4>FOUNDER 0{partyId + 1}</h4><AccountInvite token={token} sessionId={session.session_id} partyId={partyId}/></div>)}
            </section>}
            <section className="ch-tool-section">
              <div className="ch-tool-heading"><span>06</span><h3>PROTOCOL EXPLAINER</h3></div>
              <details className="ch-drawer-guide"><summary>HOW THE THREE-PARTY COMPUTATION WORKS</summary><div><ProtocolWalkthrough /></div></details>
            </section>
          </div>
          <div className="ch-drawer-foot"><span><LockKeyhole size={13}/> INDIVIDUAL SALARIES NEVER DISPLAYED</span></div>
        </section>
      </div>}
    </main>
  );
}