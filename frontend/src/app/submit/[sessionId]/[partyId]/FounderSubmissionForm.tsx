"use client";

import { FormEvent, useMemo, useState } from "react";
import { ArrowRight, Check, CircleAlert, LockKeyhole, ShieldCheck } from "lucide-react";
import { OperationsFounderArtwork } from "../../../OperationsScreens";

const partyUrls: Record<string, string | undefined> = {
  "0": process.env.NEXT_PUBLIC_PARTY_0_URL,
  "1": process.env.NEXT_PUBLIC_PARTY_1_URL,
  "2": process.env.NEXT_PUBLIC_PARTY_2_URL,
};

export default function FounderSubmissionForm({ sessionId, partyId, accountCapability }: {
  sessionId: string;
  partyId: string;
  accountCapability?: string;
}) {
  const [salary, setSalary] = useState("");
  const [capability, setCapability] = useState(accountCapability || "");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const validParty = ["0", "1", "2"].includes(partyId);
  const partyUrl = useMemo(() => partyUrls[partyId]?.replace(/\/+$/, ""), [partyId]);
  const armed = Boolean(salary.trim()) && !submitted;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    if (!validParty || !partyUrl) {
      setError("This invitation has an invalid party configuration. Contact the session administrator.");
      return;
    }
    if (!capability.trim()) {
      setError("Enter the one-time founder capability supplied with your invitation.");
      return;
    }
    if (!salary.trim()) {
      setError("Enter your salary as a whole number.");
      return;
    }
    const amount = Number(salary);
    if (!Number.isSafeInteger(amount) || amount < 0) {
      setError("Enter a whole, non-negative salary amount.");
      return;
    }

    setSubmitting(true);
    try {
      // Direct browser-to-party submission. Never routed through the coordinator.
      const response = await fetch(`${partyUrl}/sessions/${encodeURIComponent(sessionId)}/input`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${capability.trim()}` },
        body: JSON.stringify({ salary: amount }),
        cache: "no-store",
        credentials: "omit",
        referrerPolicy: "no-referrer",
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Submission failed with HTTP ${response.status}`);
      if (data.party_id !== Number(partyId) || data.input_submitted !== true) {
        throw new Error("The assigned party did not confirm this submission. Contact the administrator.");
      }
      setSalary("");
      setCapability("");
      setSubmitted(true);
      setMessage("Your private input was accepted by your assigned MPC party. You may close this page.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Private submission failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="vb-ops">
      <section id="panel-founder" className={`panel active founder-panel ${armed ? "is-armed" : ""} ${submitting ? "is-sending" : ""} ${submitted ? "is-sealed sealed" : ""}`} aria-label="Private founder input">
        <OperationsFounderArtwork partyId={validParty ? partyId : "0"} armed={armed} sending={submitting} sealed={submitted}/>
        <div className="founder-right">
          <div className="panel-eyebrow">PRIVATE CHANNEL / FOUNDER 0{validParty ? Number(partyId)+1 : "–"}</div>
          <h1 className="impact"><span>SUBMIT</span><span>YOUR SALARY.</span></h1>
          <p className="panel-eyebrow">YOUR VALUE REMAINS PRIVATE.</p>
          {!validParty ? <p className="submit-status" role="alert">Invalid party assignment. Contact the administrator.</p>
          : submitted ? <div className="founder-submission-confirmed" role="status" aria-live="polite"><Check size={30}/> INPUT SEALED.<p className="submit-status">{message}</p></div>
          : <form className="founder-form" onSubmit={submit}>
              <label className="founder-label" htmlFor="rb-salary">SALARY AMOUNT / WHOLE NUMBER</label>
              <div className="salary-shell"><input id="rb-salary" name="salary" type="text" inputMode="numeric" autoComplete="off" value={salary} onChange={event=>setSalary(event.target.value)} disabled={submitting} placeholder="Enter your salary" required aria-describedby="rb-private-note" /></div>
              {!accountCapability && <div className="capability-row"><label htmlFor="rb-capability">ONE-TIME PRIVATE CAPABILITY</label><input id="rb-capability" type="password" autoComplete="off" value={capability} onChange={event=>setCapability(event.target.value)} disabled={submitting} placeholder="Enter private token" required /></div>}
              <button type="submit" className="primary" disabled={submitting}><LockKeyhole size={24}/>{submitting ? "SENDING PRIVATELY…" : "SEAL & SUBMIT"}<ArrowRight size={24}/></button>
              <div className="founder-privacy" id="rb-private-note"><ShieldCheck size={19}/><div>Single-use private input. Sent directly to your assigned MPC party, never to the coordinator.</div></div>
            </form>}
          {error && <p className="submit-status" role="alert"><CircleAlert size={17}/> {error}</p>}
          {message && !submitted && <p className="submit-status" role="status">{message}</p>}
        </div>
      </section>
    </main>
  );
}