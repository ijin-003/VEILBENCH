"use client";

import { FormEvent, useMemo, useState } from "react";
import { ArrowRight, Check, CircleAlert, LockKeyhole, ShieldCheck } from "lucide-react";
import "../../../approved-board.css";

const partyUrls: Record<string, string | undefined> = {
  "0": process.env.NEXT_PUBLIC_PARTY_0_URL,
  "1": process.env.NEXT_PUBLIC_PARTY_1_URL,
  "2": process.env.NEXT_PUBLIC_PARTY_2_URL,
};

/** Static art only; it never receives, draws, or stores the salary. */
export function PrivateMark({ active, sending, sealed, partyId }: {
  active: boolean;
  sending: boolean;
  sealed: boolean;
  partyId: string;
}) {
  return (
    <div className={`d4-mark vb-ref-private-mark ${active ? "d4-mark--active" : ""} ${sending ? "d4-mark--sending" : ""} ${sealed ? "d4-mark--sealed" : ""}`}>
      <svg viewBox="0 0 570 715" role="img" aria-label={sealed ? "Private input accepted and sealed" : sending ? "Sending to assigned MPC party" : "Anonymous founder inside protected input vessel"}>
        <defs>
          <linearGradient id="vb-private-steel" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#fff7e5"/><stop offset=".25" stopColor="#c8a89d"/><stop offset=".53" stopColor="#fff9ed"/><stop offset=".78" stopColor="#a8a5a2"/><stop offset="1" stopColor="#201316"/>
          </linearGradient>
          <linearGradient id="vb-private-glass" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#8b0c19"/><stop offset=".5" stopColor="#fa2138"/><stop offset="1" stopColor="#6b0918"/>
          </linearGradient>
        </defs>
        <path d="M0 160 370 0H570V715H0Z" fill="#e90e24" opacity=".3"/>
        <path d="M64 111V611Q68 692 284 702Q501 685 506 613V110Q487 44 287 40Q86 48 64 111Z" fill="#111010" stroke="#111" strokeWidth="15"/>
        <path d="M105 128V610Q115 661 288 665Q461 657 465 610V128Q461 82 289 86Q114 88 105 128Z" fill="url(#vb-private-glass)" stroke="#ffedd8" strokeWidth="13"/>
        <path d="M129 167V578" fill="none" stroke="#fff6e6" strokeWidth="12" opacity=".64"/>
        <path d="M440 163V575" fill="none" stroke="#ffd0c7" strokeWidth="8" opacity=".55"/>
        {/* Anonymous founder silhouette, with sharp comic hair and a clean neck/shoulder line. */}
        <path d="M186 491Q173 449 192 416L173 383 192 346 181 320 205 328 212 294 231 303 247 271 263 288 289 275 301 293 321 283 322 316 350 312 340 337 364 350 341 365 354 390 340 418 335 451 319 474 332 515 382 548 427 586 427 634H156Q143 585 182 558L227 519 222 492Z" fill="#171112"/>
        <path d="M331 383Q350 394 353 403L336 408Q338 431 319 443L303 437 292 458 269 449 262 483" fill="none" stroke="#f5e2d3" strokeWidth="5" opacity=".7"/>
        <path d="M177 644Q193 566 240 543L265 525 285 539 301 518 343 547Q389 565 400 644" fill="#101112"/>
        {/* Perspective shell: exposed black/red/steel rings top and bottom */}
        <ellipse cx="286" cy="116" rx="223" ry="79" fill="#121010" stroke="#161010" strokeWidth="16"/>
        <ellipse cx="286" cy="110" rx="218" ry="69" fill="url(#vb-private-steel)" stroke="#120d0d" strokeWidth="13"/>
        <ellipse cx="286" cy="110" rx="170" ry="43" fill="#201213" stroke="#f9e8dc" strokeWidth="9"/>
        <ellipse cx="286" cy="108" rx="123" ry="25" fill="#a80b1b" stroke="#150b0c" strokeWidth="10"/>
        <path d="M74 122Q284 195 497 119" fill="none" stroke="#151010" strokeWidth="16"/>
        <path d="M66 132Q282 213 503 129" fill="none" stroke="#fff6ea" strokeWidth="7"/>
        <path d="M89 598Q281 667 483 601" fill="none" stroke="#101010" strokeWidth="23"/>
        <ellipse cx="283" cy="639" rx="209" ry="53" fill="#161111" stroke="#f9e9da" strokeWidth="15"/>
        <ellipse cx="283" cy="649" rx="171" ry="34" fill="#941020" stroke="#1b0e0e" strokeWidth="11"/>
        <path d="M86 665Q281 714 476 665" fill="none" stroke="#0f0c0c" strokeWidth="12"/>
        {/* Slanted seal crosses the chamber like the approved board. */}
        <g transform="rotate(-13 284 470)">
          <rect x="47" y="436" width="470" height="110" fill="#fff8eb" stroke="#111" strokeWidth="8"/>
          <path d="M72 479v-18a20 20 0 0 1 40 0v18" fill="none" stroke="#111" strokeWidth="9"/>
          <rect x="65" y="476" width="53" height="42" rx="4" fill="#141111"/>
          <text x="141" y="479" fontFamily="Arial,sans-serif" fontStyle="italic" fontWeight="900" fontSize="30" fill="#111">PRIVATE INPUT</text>
          <text x="141" y="518" fontFamily="Arial,sans-serif" fontStyle="italic" fontWeight="900" fontSize="36" fill="#111">{sealed ? "SEALED" : "SEAL"}</text>
        </g>
        {sealed && <path d="M215 270 270 330 361 221" fill="none" stroke="#fff8ed" strokeWidth="21" strokeLinecap="round"/>}
        <text x="472" y="686" fill="#fff8ea" textAnchor="end" fontFamily="Arial,sans-serif" fontWeight="900" fontSize="20">0{Number(partyId)+1}</text>
      </svg>
      <span className="d4-mark-caption">{sealed ? "RECEIPT VERIFIED" : sending ? "SUBMISSION IN PROGRESS" : "PRIVATE CHANNEL"}</span>
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
          <h1>SUBMIT YOUR <em>SALARY.</em></h1>
          <p className="d4-intro">YOUR VALUE REMAINS PRIVATE. ONE DIRECT SUBMISSION TO YOUR ASSIGNED MPC PARTY.</p>
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
