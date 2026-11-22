"use client";

import { FormEvent, useMemo, useState } from "react";
import { ArrowRight, Check, CircleAlert, LockKeyhole, ShieldCheck } from "lucide-react";

const partyUrls: Record<string, string | undefined> = {
  "0": process.env.NEXT_PUBLIC_PARTY_0_URL,
  "1": process.env.NEXT_PUBLIC_PARTY_1_URL,
  "2": process.env.NEXT_PUBLIC_PARTY_2_URL,
};

/** Static art only; it never receives, draws, or stores the salary. */
function PrivateMark({ active, sending, sealed, partyId }: {
  active: boolean;
  sending: boolean;
  sealed: boolean;
  partyId: string;
}) {
  return (
    <div className={`d4-mark ${active ? "d4-mark--active" : ""} ${sending ? "d4-mark--sending" : ""} ${sealed ? "d4-mark--sealed" : ""}`}>
      <svg viewBox="0 0 500 480" role="img" aria-label={sealed ? "Private input accepted by the assigned MPC party" : sending ? "Transmitting to the assigned MPC party" : "Private input seal, awaiting submission"}>
        <path className="d4-mark-wedge" d="M0 48L500 0V138L148 480H0Z" />
        <path className="d4-mark-black" d="M345 0H500V480H417L233 284Z" />
        <g className="d4-mark-orbit">
          <circle cx="247" cy="244" r="143" className="d4-mark-circle"/>
          <path d="M247 95v35M247 358v35M98 244h35M361 244h35" className="d4-mark-index" />
        </g>
        <circle cx="247" cy="244" r="112" className="d4-mark-disc" />
        <path d="M183 199H311V295H183Z" className="d4-mark-frame"/>
        <path className="d4-mark-lock" d={sealed ? "M204 243l28 27 61-62" : "M217 223v-19a30 30 0 0 1 60 0v19M201 224H293V287H201Z"} />
        <path d="M50 380H147M352 110H448" className="d4-mark-stroke" />
        <text x="28" y="455" className="d4-mark-number">0{Number(partyId) + 1}</text>
      </svg>
      <span className="d4-mark-caption">{sealed ? "RECEIPT VERIFIED" : sending ? "SECURE TRANSFER" : active ? "READY TO SEAL" : "PRIVATE CHANNEL"}</span>
    </div>
  );
}

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
    <main className={`d4-root ${armed ? "d4-root--armed" : ""} ${submitting ? "d4-root--sending" : ""} ${submitted ? "d4-root--sealed" : ""}`}>
      <section className="d4-art" aria-label="Private-channel illustration">
        <div className="d4-art-head">VEILBENCH <span>//</span> PRIVATE / 0{validParty ? Number(partyId) + 1 : "–"}</div>
        <PrivateMark active={armed} sending={submitting} sealed={submitted} partyId={validParty ? partyId : "0"} />
        <div className="d4-art-foot">CONFIDENTIAL <span>—</span> SINGLE USE</div>
      </section>
      <section className="d4-work" aria-label="Private founder submission">
        <div className="d4-work-top">PARTY {validParty ? String(Number(partyId) + 1).padStart(2, "0") : "—"} <span>DIRECT MPC CHANNEL</span></div>
        <div className="d4-work-content">
          <span className="d4-kicker">01 / PRIVATE INPUT</span>
          <h1>MAKE IT <em>PRIVATE.</em></h1>
          <p className="d4-intro">One submission. Sent directly to your assigned MPC party—not the coordinator.</p>
          {!validParty ? (
            <div className="d4-alert" role="alert"><CircleAlert size={18}/> Invalid party assignment. Contact the administrator.</div>
          ) : submitted ? (
            <div className="d4-success" role="status" aria-live="polite">
              <Check size={28} aria-hidden="true"/><strong>INPUT SEALED.</strong><p>{message}</p>
            </div>
          ) : (
            <form className="d4-form" onSubmit={submit}>
              <label htmlFor="d4-salary">SALARY AMOUNT <span>WHOLE NUMBER</span></label>
              <input id="d4-salary" name="salary" type="text" inputMode="numeric" autoComplete="off" value={salary} onChange={event => setSalary(event.target.value)} disabled={submitting} placeholder="Enter amount" required aria-describedby="d4-note"/>
              <p id="d4-note">Your amount will never appear on the administrator dashboard.</p>
              {!accountCapability && <>
                <label htmlFor="d4-capability">ONE-TIME CAPABILITY</label>
                <div className="d4-token"><LockKeyhole size={18} aria-hidden="true"/><input id="d4-capability" type="password" autoComplete="off" value={capability} onChange={event => setCapability(event.target.value)} disabled={submitting} placeholder="Private token" required/></div>
              </>}
              <button type="submit" disabled={submitting} className="d4-submit"><span>{submitting ? "SENDING PRIVATELY…" : "SEAL & SUBMIT"}</span><ArrowRight size={22} aria-hidden="true"/></button>
            </form>
          )}
          {error && <p className="d4-alert" role="alert"><CircleAlert size={17} aria-hidden="true"/>{error}</p>}
          {message && !submitted && <p role="status" className="d4-alert">{message}</p>}
          <p className="d4-privacy"><ShieldCheck size={17} aria-hidden="true"/> Single use · Keep your invitation private.</p>
        </div>
        <div className="d4-work-bottom">PRIVATE DEPOSIT <span>///</span> VEILBENCH</div>
      </section>
    </main>
  );
}
