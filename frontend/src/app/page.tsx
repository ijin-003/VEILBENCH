"use client";
import { FormEvent, useEffect, useRef, useState } from "react";
import AdminDashboard from "./AdminDashboard";
import VanguardHero from "./VanguardHero";
import AuthGateway from "./AuthGateway";
import { GuidedTour } from "./LearningCenter";
import FounderSubmissionForm from "./submit/[sessionId]/[partyId]/FounderSubmissionForm";
const api = (process.env.NEXT_PUBLIC_API_URL || "https://localhost:8000").replace(/\/+$/, "");
type Identity = { token: string; role: string; username: string };
type Assignment = { session_id: string; party_id: number; capability: string };

export default function HomePage() {
    const [identity, setIdentity] = useState<Identity | null>(null);
    const [showLanding, setShowLanding] = useState(true);
    const [leavingLanding, setLeavingLanding] = useState(false);
    const transitionTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
    useEffect(() => () => { if (transitionTimer.current) clearTimeout(transitionTimer.current); }, []);
    function beginLoginTransition() {
      if (leavingLanding) return;
      if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        setShowLanding(false);
        return;
      }
      setLeavingLanding(true);
      transitionTimer.current = setTimeout(() => {
        setShowLanding(false);
        setLeavingLanding(false);
        transitionTimer.current = null;
      }, 640);
    }
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
  if (!identity && showLanding) {
    return <>
      <VanguardHero onStart={beginLoginTransition} />
      {leavingLanding && <div className="vb-access-wipe" aria-hidden="true"><span>ACCESS / INITIATING</span></div>}
    </>;
  }
  if (identity?.role === "admin") return (
    <div className="ch-app-layout">
      <nav className="ch-app-nav" aria-label="Administrator navigation">
        <div className="ch-app-brand"><i aria-hidden="true"/><b>VEILBENCH</b><small>/ CHAMBER ACCESS</small></div>
        <div className="ch-app-controls">
          <GuidedTour role="admin" />
          <button type="button" disabled={busy} onClick={() => void logout()}>SIGN OUT</button>
        </div>
      </nav>
      {message && <p role="alert" className="p-3 text-rose-300">{message}</p>}
      <AdminDashboard token={identity.token} />
    </div>
  );
  if (identity) return <>
    <nav className="flex flex-wrap items-center justify-between gap-3 bg-slate-900 p-4 text-slate-100"><span>{identity.username} · {identity.role}</span><div className="flex flex-wrap items-center gap-2"><GuidedTour role="participant" /><button className="button-secondary" disabled={busy} onClick={() => void logout()}>Sign out</button></div></nav>
    {message && <p role="alert" className="p-4 text-rose-500">{message}</p>}
    {assignment ? <FounderSubmissionForm sessionId={assignment.session_id} partyId={String(assignment.party_id)} accountCapability={assignment.capability} /> : <p className="p-6">No active assignment.</p>}
  </>;
  return (
    <AuthGateway
      activate={activate}
      busy={busy}
      message={message}
      username={username}
      password={password}
      invitation={invitation}
      onUsernameChange={setUsername}
      onPasswordChange={setPassword}
      onInvitationChange={setInvitation}
      onSubmit={submit}
      onToggleActivate={() => {
        setActivate(!activate);
        setPassword("");
        setInvitation("");
        setMessage("");
      }}
      onBack={() => {
        setShowLanding(true);
        setMessage("");
        setPassword("");
        setInvitation("");
      }}
    />
  );
}
