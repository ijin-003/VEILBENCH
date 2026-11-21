"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { CheckCircle2, Clipboard, Lock, Play, Plus, RefreshCw, Server } from "lucide-react";

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

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://localhost:8000";

export default function HomePage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [adminToken, setAdminToken] = useState("");
  const [session, setSession] = useState<SessionData | null>(null);
  const [loading, setLoading] = useState(false);
  const [healthLoading, setHealthLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkHealth = useCallback(async () => {
    setHealthLoading(true);
    try {
      const response = await fetch(`${apiUrl}/api/v1/health`, { referrerPolicy: "no-referrer" });
      if (!response.ok) throw new Error(`Backend returned HTTP ${response.status}`);
      setHealth(await response.json());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not reach the backend");
    } finally {
      setHealthLoading(false);
    }
  }, []);

  useEffect(() => {
    void checkHealth();
  }, [checkHealth]);

  async function managementRequest(path: string, method: "GET" | "POST", body?: object) {
    if (!adminToken) throw new Error("Enter the coordinator management token first.");
    const response = await fetch(`${apiUrl}/api/v1${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        "X-VEILBENCH-Admin-Token": adminToken,
      },
      body: body ? JSON.stringify(body) : undefined,
      credentials: "omit",
      referrerPolicy: "no-referrer",
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `Request failed with HTTP ${response.status}`);
    return data as SessionData;
  }

  async function createSession(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      setSession(await managementRequest("/sessions", "POST", { ttl_minutes: 30 }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not create the session");
    } finally {
      setLoading(false);
    }
  }

  async function refreshSession() {
    if (!session) return;
    setLoading(true);
    setError(null);
    try {
      const next = await managementRequest(`/sessions/${session.session_id}`, "GET");
      setSession({ ...next, founder_invites: session.founder_invites });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not refresh the session");
    } finally {
      setLoading(false);
    }
  }

  async function computeSession() {
    if (!session) return;
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

  async function copy(value: string) {
    await navigator.clipboard.writeText(value);
  }

  return (
    <main className="min-h-screen bg-slate-950 p-6 text-slate-100">
      <div className="mx-auto max-w-4xl space-y-6">
        <header className="space-y-2 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-800 bg-indigo-950/70 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-indigo-300">
            <Lock className="h-3.5 w-3.5" /> private three-party salary benchmark
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight text-indigo-300">VEILBENCH</h1>
          <p className="mx-auto max-w-2xl text-sm text-slate-400">
            Founder salaries are submitted directly to assigned MPC parties. This coordinator only manages
            session metadata and receives the final aggregate.
          </p>
        </header>

        <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-5">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2"><Server className="h-5 w-5 text-indigo-400" /><h2 className="font-semibold">Backend status</h2></div>
            <button className="button-secondary" onClick={() => void checkHealth()} disabled={healthLoading}>
              <RefreshCw className="h-4 w-4" /> Refresh
            </button>
          </div>
          {health ? (
            <div className="mt-4 flex items-start gap-3 text-sm text-emerald-300">
              <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" />
              <p>{health.service} v{health.version}: {health.status}. Session storage: {health.session_storage || "unknown"}.</p>
            </div>
          ) : <p className="mt-4 text-sm text-slate-400">{healthLoading ? "Checking connectivity…" : "Backend is unavailable."}</p>}
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/70 p-5">
          <h2 className="font-semibold">Coordinator management</h2>
          <p className="mt-1 text-sm text-slate-400">The management token stays in this browser tab and is never saved.</p>
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
            <button className="button-primary" type="submit" disabled={loading}><Plus className="h-4 w-4" /> Create 30-minute session</button>
          </form>
          {error && <p role="alert" className="mt-3 text-sm text-rose-300">{error}</p>}
        </section>

        {session && (
          <section className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/70 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div><h2 className="font-semibold">Session {session.session_id}</h2><p className="text-sm text-slate-400">State: {session.state} · expires {new Date(session.expires_at).toLocaleTimeString()}</p></div>
              <div className="flex gap-2">
                <button className="button-secondary" onClick={() => void refreshSession()} disabled={loading}><RefreshCw className="h-4 w-4" /> Check submissions</button>
                <button className="button-primary" onClick={() => void computeSession()} disabled={loading || session.submitted_party_ids.length !== 3}><Play className="h-4 w-4" /> Compute aggregate</button>
              </div>
            </div>

            {session.founder_invites && <>
              <p className="text-sm text-amber-200">Share each link and its capability token only with the matching founder, through a secure channel. Tokens are shown once and are not stored by the coordinator.</p>
              <div className="grid gap-3 md:grid-cols-3">
                {session.founder_invites.map((invite) => (
                  <article key={invite.party_id} className="rounded-lg border border-slate-700 bg-slate-950 p-4 text-sm">
                    <h3 className="font-semibold text-indigo-300">Founder {invite.party_id + 1}</h3>
                    <a className="mt-2 block break-all text-sky-300 underline" href={invite.submission_page} target="_blank" rel="noreferrer">Open private submission page</a>
                    <button className="button-secondary mt-3 w-full" onClick={() => void copy(invite.capability_token)}><Clipboard className="h-4 w-4" /> Copy one-time capability</button>
                  </article>
                ))}
              </div>
            </>}

            <p className="text-sm text-slate-300">Submitted: {session.submitted_party_ids.length}/3 founders ({session.submitted_party_ids.map((id) => id + 1).join(", ") || "none"})</p>
            {session.result && <div className="rounded-lg border border-emerald-800 bg-emerald-950/40 p-4 text-emerald-200">Aggregate: {session.result.aggregate_sum.toLocaleString()} · Average: {session.result.average_salary.toLocaleString()}</div>}
            {session.failure_reason && <p className="text-sm text-rose-300">{session.failure_reason}</p>}
          </section>
        )}
      </div>
    </main>
  );
}
