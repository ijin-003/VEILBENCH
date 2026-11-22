"use client";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
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
    const [curtain, setCurtain] = useState<"access" | "home" | "admin" | "participant" | "logout" | null>(null);
    const navigationLocked = useRef(false);
    const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
    const identityRef = useRef<Identity | null>(null);
    const accessEntryAdded = useRef(false);

    useEffect(() => { identityRef.current = identity; }, [identity]);
    useEffect(() => () => {
      timers.current.forEach(clearTimeout);
      timers.current = [];
    }, []);

    const navigateWithCurtain = useCallback((action: () => void, target: "access" | "home" | "admin" | "participant" | "logout") => {
      if (navigationLocked.current) return;
      if (typeof window === "undefined" || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        action();
        return;
      }
      navigationLocked.current = true;
      setCurtain(target);
      timers.current.push(setTimeout(action, 360));
      timers.current.push(setTimeout(() => {
        setCurtain(null);
        navigationLocked.current = false;
      }, 820));
    }, []);

    function beginLoginTransition() {
      if (navigationLocked.current) return;
      const url = new URL(window.location.href);
      url.searchParams.set("view", "access");
      window.history.pushState({ ...window.history.state, vbScreen: "access" }, "", url.toString());
      accessEntryAdded.current = true;
      navigateWithCurtain(() => setShowLanding(false), "access");
    }

    function returnToLanding() {
      if (navigationLocked.current || busy) return;
      setMessage("");
      setPassword("");
      setInvitation("");
      navigateWithCurtain(() => {
        setShowLanding(true);
        accessEntryAdded.current = false;
        const url = new URL(window.location.href);
        url.searchParams.delete("view");
        window.history.replaceState({ ...window.history.state, vbScreen: "home" }, "", url.toString());
      }, "home");
    }

    useEffect(() => {
      function handlePopState(event: PopStateEvent) {
        // Only public pages are managed in browser history. Never restore an
        // authenticated workspace from the Back/Forward cache.
        if (identityRef.current) return;
        const toAccess = event.state?.vbScreen === "access";
        accessEntryAdded.current = toAccess;
        navigateWithCurtain(() => setShowLanding(!toAccess), toAccess ? "access" : "home");
      }
      window.addEventListener("popstate", handlePopState);
      return () => window.removeEventListener("popstate", handlePopState);
    }, [navigateWithCurtain]);
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
        if (result.role === "admin" || result.role === "participant") {
          navigateWithCurtain(() => {
            setAssignment(assignedData);
            setIdentity(result);
          }, result.role);
        } else {
          setAssignment(assignedData);
          setIdentity(result);
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
      navigateWithCurtain(() => {
        setIdentity(null);
        setAssignment(null);
        setMessage("");
        setShowLanding(false);
        const url = new URL(window.location.href);
        url.searchParams.delete("view");
        window.history.replaceState({ ...window.history.state, vbScreen: "access" }, "", url.toString());
        accessEntryAdded.current = false;
      }, "logout");
    } catch { setMessage("Sign-out failed. Please retry."); }
    finally { setBusy(false); }
  }
  const curtainLayer = curtain && <div className={`v4-route-curtain v4-route-curtain--${curtain}`} aria-hidden="true"><div className="v4-route-blade"/><span>VEILBENCH <b>///</b></span></div>;
  if (!identity && showLanding) {
    return <><VanguardHero onStart={beginLoginTransition} />{curtainLayer}</>;
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
      {curtainLayer}
    </div>
  );
  if (identity) return <>
    <nav className="pv-account-nav" aria-label="Participant navigation">
      <span className="pv-account-brand"><b>VEILBENCH</b><small>/ PRIVATE CHANNEL</small></span>
      <div className="pv-account-actions"><span className="pv-account-username">{identity.username}</span><GuidedTour role="participant" /><button type="button" disabled={busy} onClick={() => void logout()}>SIGN OUT</button></div>
    </nav>
    {message && <p role="alert" className="pv-account-notice">{message}</p>}
    {assignment ? <FounderSubmissionForm sessionId={assignment.session_id} partyId={String(assignment.party_id)} accountCapability={assignment.capability} /> : <div className="pv-account-notice" role="status">No active assignment. Contact the administrator.</div>}
    {curtainLayer}
  </>;
  return (
    <>
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
      onBack={returnToLanding}
    />
    {curtainLayer}
    </>
  );
}
