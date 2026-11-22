"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  CheckCircle2,
  Clipboard,
  Copy,
  ExternalLink,
  Lock,
  Play,
  Plus,
  RefreshCw,
  Server,
  ShieldCheck,
  Users,
} from "lucide-react";

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

function stateStyle(state: string): string {
  switch (state.toLowerCase()) {
    case "completed":
      return "border-emerald-700 bg-emerald-950/50 text-emerald-300";
    case "ready":
      return "border-sky-700 bg-sky-950/50 text-sky-300";
    case "computing":
      return "border-amber-700 bg-amber-950/50 text-amber-300";
    case "failed":
    case "expired":
      return "border-rose-700 bg-rose-950/50 text-rose-300";
    default:
      return "border-slate-700 bg-slate-800 text-slate-300";
  }
}

export default function HomePage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [adminToken, setAdminToken] = useState("");
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
          "X-VEILBENCH-Admin-Token": adminToken,
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

  return (
    <main className="min-h-screen bg-slate-950 p-6 text-slate-100">
      <div className="mx-auto max-w-5xl space-y-6">
        <header className="space-y-2 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-800 bg-indigo-950/70 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-indigo-300">
            <Lock className="h-3.5 w-3.5" /> private three-party salary benchmark
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight text-indigo-300">VEILBENCH</h1>
          <p className="mx-auto max-w-2xl text-sm text-slate-400">
            Three founders submit independently to their assigned MPC parties. The coordinator manages
            session metadata and receives only the final aggregate result.
          </p>
        </header>

        <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-5">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Server className="h-5 w-5 text-indigo-400" />
              <h2 className="font-semibold">Backend status</h2>
            </div>
            <button
              className="button-secondary"
              onClick={() => {
                setHealthLoading(true);
                void checkHealth();
              }}
              disabled={healthLoading}
            >
              <RefreshCw className="h-4 w-4" /> Refresh
            </button>
          </div>
          {health ? (
            <div className="mt-4 flex items-start gap-3 text-sm text-emerald-300">
              <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" />
              <p>
                {health.service} v{health.version}: {health.status}. Session storage: {health.session_storage || "unknown"}.
              </p>
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-400">
              {healthLoading ? "Checking connectivity…" : "Backend is unavailable."}
            </p>
          )}
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-5">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-indigo-400" />
            <h2 className="font-semibold">Coordinator management</h2>
          </div>
          <p className="mt-1 text-sm text-slate-400">
            The management token stays in this browser tab. It is not saved in browser storage.
          </p>
          <form className="mt-4 flex flex-col gap-3 sm:flex-row" onSubmit={createSession}>
            <input
              className="input flex-1"
              type="password"
              autoComplete="off"
              placeholder="Coordinator management token"
              value={adminToken}
              onChange={(event) => setAdminToken(event.target.value)}
              aria-label="Coordinator management token"
            />
            <button className="button-primary" type="submit" disabled={loading || !adminToken.trim()}>
              <Plus className="h-4 w-4" /> Create 30-minute session
            </button>
          </form>
          <form className="mt-4 flex flex-col gap-3 border-t border-slate-800 pt-4 sm:flex-row" onSubmit={loadExistingSession}>
            <input
              className="input flex-1"
              type="text"
              autoComplete="off"
              placeholder="Existing session ID"
              value={sessionLookupId}
              onChange={(event) => setSessionLookupId(event.target.value)}
              aria-label="Existing session ID"
            />
            <button className="button-secondary" type="submit" disabled={loading || !adminToken.trim() || !sessionLookupId.trim()}>
              Load existing session
            </button>
          </form>
          {error && <p role="alert" className="mt-3 text-sm text-rose-300">{error}</p>}
        </section>

        {session && (
          <section className="space-y-5 rounded-xl border border-slate-800 bg-slate-900/70 p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="font-semibold">Benchmark session</h2>
                <p className="mt-1 break-all font-mono text-xs text-slate-400">{session.session_id}</p>
                <p className="mt-2 text-sm text-slate-400">
                  Expires {new Date(session.expires_at).toLocaleString()}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase ${stateStyle(session.state)}`}>
                  {session.state}
                </span>
                <button className="button-secondary" onClick={() => void refreshSession()} disabled={loading}>
                  <RefreshCw className="h-4 w-4" /> Check now
                </button>
                <button className="button-primary" onClick={() => void computeSession()} disabled={loading || !canCompute}>
                  <Play className="h-4 w-4" /> Compute aggregate
                </button>
              </div>
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Users className="h-5 w-5 text-indigo-300" />
                  <h3 className="font-medium">Founder submissions</h3>
                </div>
                <span className="text-sm font-semibold text-slate-200">{session.submitted_party_ids.length}/3 received</span>
              </div>
              <div className="mt-3 grid gap-3 sm:grid-cols-3">
                {[0, 1, 2].map((partyId) => (
                  <div key={partyId} className="flex items-center gap-2 rounded-md border border-slate-800 p-3">
                    {submitted.has(partyId) ? (
                      <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                    ) : (
                      <span className="h-5 w-5 rounded-full border border-slate-600" />
                    )}
                    <div>
                      <p className="text-sm font-medium">Founder {partyId + 1}</p>
                      <p className="text-xs text-slate-400">{submitted.has(partyId) ? "Input received" : "Awaiting submission"}</p>
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-xs text-slate-500">
                {session.state.toLowerCase() === "ready"
                  ? "All three parties have confirmed receipt. Computation is available."
                  : "Status refreshes automatically every four seconds while this session is active."}
              </p>
              {pollWarning && <p role="status" className="mt-2 text-xs text-amber-300">Status refresh warning: {pollWarning}</p>}
            </div>

            {session.founder_invites && session.state.toLowerCase() !== "completed" && (
              <div className="space-y-3">
                <div>
                  <h3 className="font-medium">Private founder invitations</h3>
                  <p className="mt-1 text-sm text-amber-200">
                    Send each founder their own submission link and one-time capability. Send the capability
                    through a separate trusted channel; never put it in the URL or a public group chat.
                  </p>
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  {session.founder_invites.map((invite) => (
                    <article key={invite.party_id} className="rounded-lg border border-slate-700 bg-slate-950 p-4 text-sm">
                      <h4 className="font-semibold text-indigo-300">Founder {invite.party_id + 1}</h4>
                      <a
                        className="mt-2 inline-flex items-center gap-1 break-all text-sky-300 underline"
                        href={invite.submission_page}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open submission page <ExternalLink className="h-3 w-3 shrink-0" />
                      </a>
                      <button
                        className="button-secondary mt-3 w-full"
                        onClick={() => void copyValue(invite.submission_page, `Founder ${invite.party_id + 1} link`)}
                      >
                        <Copy className="h-4 w-4" /> Copy submission link
                      </button>
                      <button
                        className="button-secondary mt-2 w-full"
                        onClick={() => void copyValue(invite.capability_token, `Founder ${invite.party_id + 1} capability`)}
                      >
                        <Clipboard className="h-4 w-4" /> Copy one-time capability
                      </button>
                    </article>
                  ))}
                </div>
                {copyNotice && <p role="status" className="text-xs text-emerald-300">{copyNotice}</p>}
              </div>
            )}

            {session.result && (
              <div className="rounded-lg border border-emerald-800 bg-emerald-950/40 p-5">
                <h3 className="font-semibold text-emerald-200">Secure computation completed</h3>
                <div className="mt-3 grid gap-4 sm:grid-cols-2">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-emerald-400">Aggregate salary</p>
                    <p className="mt-1 text-2xl font-bold text-emerald-100">{numberFormat.format(session.result.aggregate_sum)}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-emerald-400">Average salary</p>
                    <p className="mt-1 text-2xl font-bold text-emerald-100">{numberFormat.format(session.result.average_salary)}</p>
                  </div>
                </div>
                <p className="mt-3 text-xs text-emerald-400">Only the aggregate and average are displayed. Individual salaries are not available to the coordinator.</p>
              </div>
            )}
            {session.failure_reason && <p role="alert" className="text-sm text-rose-300">{session.failure_reason}</p>}
          </section>
        )}
      </div>
    </main>
  );
}
