"use client";
import { useState } from "react";
const api = (process.env.NEXT_PUBLIC_API_URL || "https://localhost:8000").replace(/\/+$/, "");
export default function AccountInvite({ token, sessionId, partyId }: { token: string; sessionId: string; partyId: number }) {
  const [username, setUsername] = useState("");
  const [invitation, setInvitation] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  async function invite() {
    setBusy(true); setMessage("");
    try {
      const response = await fetch(`${api}/api/v1/accounts/invitations`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify({ username, session_id: sessionId, party_id: partyId }), cache: "no-store", credentials: "omit" });
      if (!response.ok) throw new Error("Invitation failed. Use a unique lowercase username and an active session.");
      setInvitation((await response.json()).invitation);
    } catch (cause) { setMessage(cause instanceof Error ? cause.message : "Invitation failed"); }
    finally { setBusy(false); }
  }
  return <div className="mt-3 space-y-2"><label className="block">Participant username<input className="input w-full" value={username} disabled={Boolean(invitation)} onChange={e => setUsername(e.target.value.toLowerCase())} /></label>
    {invitation ? <><label className="block">Private invitation code<input className="input w-full" readOnly type="password" value={invitation} /></label><button className="button-secondary" onClick={() => { void navigator.clipboard.writeText(invitation).then(() => setMessage("Token copied. Share privately; it cannot be retrieved later."), () => setMessage("Clipboard unavailable.")); }}>Copy token only</button></> : <button className="button-primary" disabled={busy || !username} onClick={() => void invite()}>Invite participant</button>}
    {message && <p role="status">{message}</p>}
  </div>;
}
