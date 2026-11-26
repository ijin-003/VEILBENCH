"use client";
import { useState } from "react";
const api = (process.env.NEXT_PUBLIC_API_URL || "https://localhost:8000").replace(/\/+$/, "");
type InviteResult = { username: string; display_name?: string | null; invitation: string };
export default function AccountInvite({ token, sessionId, partyId }: { token: string; sessionId: string; partyId: number }) {
  const [name, setName] = useState("");
  const [issued, setIssued] = useState<InviteResult | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  async function invite(reissue = false) {
    if (busy) return;
    setBusy(true); setMessage("");
    try {
      const response = await fetch(`${api}/api/v1/accounts/invitations${reissue ? "/reissue" : ""}`, {
        method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ ...(!reissue ? { display_name: name.trim() } : {}), session_id: sessionId, party_id: partyId }),
        cache: "no-store", credentials: "omit",
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Check the founder name and session details.");
      setIssued(data);
      setMessage(reissue ? "New token issued. Previous invitation is invalid." : "Invitation created. Share the login ID and token privately.");
    } catch (cause) { setMessage(cause instanceof Error ? cause.message : "Invitation failed"); }
    finally { setBusy(false); }
  }
  async function copy(value: string, label: string) {
    try { await navigator.clipboard.writeText(value); setMessage(label + " copied."); }
    catch { setMessage("Clipboard unavailable. Select and copy the field manually."); }
  }
  return <div className="mt-3 space-y-2">
    <label className="block">Founder display name (duplicates allowed)<input className="input w-full" maxLength={80} value={name} disabled={Boolean(issued) || busy} onChange={e => setName(e.target.value)} /></label>
    {issued ? <>
      {issued.display_name && <p><small>Founder: <strong>{issued.display_name}</strong></small></p>}
      <label className="block">Unique login ID<input className="input w-full" readOnly value={issued.username} /></label>
      <button type="button" className="button-secondary" onClick={() => void copy(issued.username, "Login ID")}>Copy login ID</button>
      <label className="block">Private invitation code<input className="input w-full" readOnly type="password" value={issued.invitation} /></label>
      <button type="button" className="button-secondary" onClick={() => void copy(issued.invitation, "Token")}>Copy token only</button>
    </> : <button type="button" className="button-primary" disabled={busy || !name.trim()} onClick={() => void invite()}>Invite participant</button>}
    <button type="button" className="button-secondary" disabled={busy} onClick={() => void invite(true)}>Reissue unused invitation</button>
    {message && <p role="status">{message}</p>}
  </div>;
}
