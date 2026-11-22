"use client";
import { FormEvent, useState } from "react";
import AdminDashboard from "./AdminDashboard";
import { GuidedTour, ProtocolWalkthrough } from "./LearningCenter";
import FounderSubmissionForm from "./submit/[sessionId]/[partyId]/FounderSubmissionForm";
const api = (process.env.NEXT_PUBLIC_API_URL || "https://localhost:8000").replace(/\/+$/, "");
type Identity = { token: string; role: string; username: string };
type Assignment = { session_id: string; party_id: number; capability: string };

export default function HomePage() {
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [invitation, setInvitation] = useState("");
  const [activate, setActivate] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage("");
    try {
      const response = await fetch(`${api}/api/v1/accounts/${activate ? "activate" : "login"}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, ...(activate ? { invitation } : {}) }),
        cache: "no-store", credentials: "omit", referrerPolicy: "no-referrer",
      });
      if (!response.ok) throw new Error("Check your credentials or invitation. After five failed attempts, wait 15 minutes.");
      const result = await response.json(); setPassword(""); setInvitation("");
      if (activate) { setActivate(false); setMessage("Account activated. Sign in with your new password."); }
      else {
        setIdentity(result);
        if (result.role === "participant") {
          const assigned = await fetch(`${api}/api/v1/accounts/assignment`, { headers: { Authorization: `Bearer ${result.token}` }, cache: "no-store", credentials: "omit" });
          if (!assigned.ok) throw new Error("Your benchmark is unavailable or expired. Contact the administrator.");
          setAssignment(await assigned.json());
        }
      }
    } catch (cause) { setMessage(cause instanceof Error ? cause.message : "Connection failed"); }
    finally { setBusy(false); }
  }
  async function logout() {
    if (!identity) return;
    setBusy(true);
    try {
      const response = await fetch(`${api}/api/v1/accounts/logout`, { method: "POST", headers: { Authorization: `Bearer ${identity.token}` }, credentials: "omit" });
      if (!response.ok && response.status !== 401) throw new Error("Sign-out failed. Please retry.");
      setIdentity(null); setAssignment(null); setMessage("");
    } catch { setMessage("Sign-out failed. Please retry."); }
    finally { setBusy(false); }
  }
  if (identity) return <>
    <nav className="flex flex-wrap items-center justify-between gap-3 bg-slate-900 p-4 text-slate-100"><span>{identity.username} · {identity.role}</span><div className="flex flex-wrap items-center gap-2"><GuidedTour role={identity.role === "admin" ? "admin" : "participant"} /><button className="button-secondary" disabled={busy} onClick={() => void logout()}>Sign out</button></div></nav>
    {message && <p role="alert" className="p-4 text-rose-500">{message}</p>}
    {identity.role === "admin" ? <AdminDashboard token={identity.token} /> : assignment ? <FounderSubmissionForm sessionId={assignment.session_id} partyId={String(assignment.party_id)} accountCapability={assignment.capability} /> : <p className="p-6">No active assignment.</p>}
    {identity.role === "admin" && <div className="mx-auto max-w-5xl px-6 pb-10"><ProtocolWalkthrough /></div>}
  </>;
  return <main className="min-h-screen bg-slate-950 p-6 text-slate-100"><section className="mx-auto mt-16 max-w-md space-y-5 rounded-xl border border-slate-800 bg-slate-900 p-6">
    <h1 className="text-3xl font-bold text-indigo-300">VEILBENCH</h1><div className="flex flex-wrap items-center justify-between gap-2"><h2>{activate ? "Activate your invitation" : "Sign in"}</h2><GuidedTour role="welcome" /></div>
    <form onSubmit={submit} className="space-y-4">
      <label className="block">Username<input required className="input mt-1 w-full" autoComplete="username" pattern="[a-z0-9][a-z0-9_.-]+" minLength={3} maxLength={80} value={username} onChange={e => setUsername(e.target.value.toLowerCase())} /></label>
      {activate && <label className="block">Invitation code<input required className="input mt-1 w-full" type="password" autoComplete="off" value={invitation} onChange={e => setInvitation(e.target.value)} /></label>}
      <label className="block">{activate ? "Choose password (12–128 characters)" : "Password"}<input required className="input mt-1 w-full" type="password" minLength={12} maxLength={128} autoComplete={activate ? "new-password" : "current-password"} value={password} onChange={e => setPassword(e.target.value)} /></label>
      <button disabled={busy} className="button-primary w-full">{busy ? "Please wait…" : activate ? "Activate account" : "Sign in"}</button>
    </form>
    <button className="button-secondary" disabled={busy} onClick={() => { setActivate(!activate); setPassword(""); setInvitation(""); setMessage(""); }}>{activate ? "Back to sign in" : "I have an invitation"}</button>
    {message && <p role="status">{message}</p>}
    <p className="text-xs text-slate-400">Three MPC processes share demonstration infrastructure. Accounts separate participation, not hosting ownership.</p>
  </section><div className="mx-auto mt-6 max-w-5xl"><ProtocolWalkthrough /></div></main>;
}
