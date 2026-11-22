"use client";
import { FormEvent, useEffect, useRef, useState } from "react";
import AdminDashboard from "./AdminDashboard";
import VanguardHero from "./VanguardHero";
import AuthGateway from "./AuthGateway";
import { GuidedTour } from "./LearningCenter";
import FounderSubmissionForm from "./submit/[sessionId]/[partyId]/FounderSubmissionForm";
import { LockKeyhole } from "lucide-react";
const api = (process.env.NEXT_PUBLIC_API_URL || "https://localhost:8000").replace(/\/+$/, "");
type Identity = { token: string; role: string; username: string };
type Assignment = { session_id: string; party_id: number; capability: string };

export default function HomePage() {
    const [identity, setIdentity] = useState<Identity | null>(null);
    const [showLanding, setShowLanding] = useState(true);
    const [leavingLanding, setLeavingLanding] = useState(false);
    const transitionTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
    const entryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
    const [entryRole, setEntryRole] = useState<"admin" | "participant" | null>(null);
    useEffect(() => () => {
      if (transitionTimer.current) clearTimeout(transitionTimer.current);
      if (entryTimer.current) clearTimeout(entryTimer.current);
    }, []);
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
        // Resolve the founder assignment before switching away from login,
        // so an expired assignment never strands the user on an empty page.
        let assignedData: Assignment | null = null;
        if (result.role === "participant") {
          const assigned = await fetch(`${api}/api/v1/accounts/assignment`, {
            headers: { Authorization: `Bearer ${result.token}` },
            cache: "no-store",
            credentials: "omit",
          });
          if (!assigned.ok) throw new Error("Your benchmark is unavailable or expired. Contact the administrator.");
          assignedData = (await assigned.json()) as Assignment;
        }
        setAssignment(assignedData);
        setIdentity(result);
        if (result.role === "admin" || result.role === "participant") {
          const prefersLessMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
          if (!prefersLessMotion) {
            setEntryRole(result.role);
            if (entryTimer.current) clearTimeout(entryTimer.current);
            entryTimer.current = setTimeout(() => {
              setEntryRole(null);
              entryTimer.current = null;
            }, 900);
          }
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
      setIdentity(null); setAssignment(null); setMessage(""); setEntryRole(null);
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
        <div className="ch-app-brand"><i aria-hidden="true"/><b>VEILBENCH</b><small>/ REACTOR CONTROL</small></div>
        <div className="ch-app-controls">
          <GuidedTour role="admin" />
          <button type="button" disabled={busy} onClick={() => void logout()}>SIGN OUT</button>
        </div>
      </nav>
      {message && <p role="alert" className="p-3 text-rose-300">{message}</p>}
      <AdminDashboard token={identity.token} />
      {entryRole === "admin" && <div className="ch-route-entry" aria-hidden="true"><span>ACCESS GRANTED <b>///</b> REACTOR ONLINE</span></div>}
    </div>
  );
  if (identity) return <>
    <nav className="pv-account-nav" aria-label="Participant navigation">
      <span className="pv-account-brand"><b>VEILBENCH</b><small>/ PRIVATE CHANNEL</small></span>
      <div className="pv-account-actions"><span className="pv-account-username">{identity.username}</span><GuidedTour role="participant" /><button type="button" disabled={busy} onClick={() => void logout()}>SIGN OUT</button></div>
    </nav>
    {message && <p role="alert" className="pv-account-notice">{message}</p>}
    {assignment ? <FounderSubmissionForm sessionId={assignment.session_id} partyId={String(assignment.party_id)} accountCapability={assignment.capability} /> : <div className="pv-account-notice" role="status">No active assignment. Contact the administrator.</div>}
    {entryRole === "participant" && <div className="pv-route-entry" aria-hidden="true"><div className="pv-route-sigil"><LockKeyhole size={32} /></div><span>PRIVATE CHANNEL ESTABLISHED</span></div>}
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
