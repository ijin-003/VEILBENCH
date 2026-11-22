"use client";

import { FormEvent, useMemo, useState } from "react";
import { ArrowRight, Check, CircleAlert, LockKeyhole, ShieldCheck } from "lucide-react";

const partyUrls: Record<string, string | undefined> = {
  "0": process.env.NEXT_PUBLIC_PARTY_0_URL,
  "1": process.env.NEXT_PUBLIC_PARTY_1_URL,
  "2": process.env.NEXT_PUBLIC_PARTY_2_URL,
};

type VaultIllustrationProps = {
  armed: boolean;
  sending: boolean;
  sealed: boolean;
  partyId: string;
};

/** The illustration never displays or receives a salary value. */
function VaultIllustration({ armed, sending, sealed, partyId }: VaultIllustrationProps) {
  return (
    <div className={`pv-illustration ${armed ? "pv-illustration--armed" : ""} ${sending ? "pv-illustration--sending" : ""} ${sealed ? "pv-illustration--sealed" : ""}`}>
      <svg viewBox="0 0 590 590" role="img" aria-label={sealed ? "Private deposit sealed and accepted" : sending ? "Submitting your private input" : "Closed private-deposit vault"}>
        <defs>
          <linearGradient id="pv-envelope" x1="0" y1="0" x2="1" y2="1">
            <stop stopColor="#fff7e9" />
            <stop offset=".52" stopColor="#e8dacc" />
            <stop offset="1" stopColor="#c8aa9e" />
          </linearGradient>
          <linearGradient id="pv-crimson" x1="0" x2="1" y1="0" y2="1">
            <stop stopColor="#ff5361" /><stop offset=".4" stopColor="#d50c31" /><stop offset="1" stopColor="#630b25" />
          </linearGradient>
          <radialGradient id="pv-shadow">
            <stop stopColor="#6b122e" stopOpacity=".25" /><stop offset="1" stopColor="#6b122e" stopOpacity="0" />
          </radialGradient>
        </defs>
        <ellipse cx="298" cy="500" rx="214" ry="43" fill="url(#pv-shadow)" />
        <g className="pv-back-rings" fill="none" stroke="#b99e9a">
          <circle cx="295" cy="268" r="202" strokeWidth="1.2" strokeDasharray="1 14" />
          <circle cx="295" cy="268" r="178" strokeWidth="2" strokeDasharray="76 18 9 18" />
          <circle cx="295" cy="268" r="157" strokeWidth="1.3" opacity=".65" />
          <path d="M295 33v28M295 475v28M60 268h28M503 268h28" strokeWidth="4" />
        </g>
        <path className="pv-aura" d="M295 52L490 156V375L295 490L100 375V156Z" fill="#df153b" opacity=".04" />
        {/* Precision lines and tiny annotations give the seal an editorial identity. */}
        <g fill="none" stroke="#bd7f86" strokeWidth="1.6" opacity=".65">
          <path d="M70 132h66M70 132v38M455 411h70M525 411v-37" />
          <path d="M75 438l48-48M515 103l-48 48" strokeDasharray="3 8" />
        </g>
        <text x="74" y="113" fontSize="11" letterSpacing="3" fontWeight="900" fill="#a34557">PRIVATE / {String(Number(partyId) + 1).padStart(2, "0")}</text>
        <text x="438" y="432" fontSize="10" letterSpacing="2.2" fontWeight="900" fill="#a34557">VB / 03</text>

        {/* Envelope shell. The value is never printed or embedded in an SVG. */}
        <g className="pv-envelope">
          <path d="M152 183L295 103L438 183V364L295 447L152 364Z" fill="#6d4d52" opacity=".19" transform="translate(0 12)" />
          <path d="M147 183L295 103L443 183V367L295 447L147 367Z" fill="url(#pv-envelope)" stroke="#4c2635" strokeWidth="4" />
          <path d="M150 184L295 296L440 184" fill="none" stroke="#a98082" strokeWidth="3" />
          <path d="M150 362L258 282M441 362L333 282" stroke="#c09893" strokeWidth="2" />
          <path className="pv-flap" d="M147 183L295 296L443 183L295 104Z" fill="#f6e9dd" stroke="#5e3640" strokeWidth="3" />
          <path d="M170 192L295 284L422 192" stroke="#c6a9a0" fill="none" strokeWidth="1.5" />
          <path d="M184 352h223" stroke="#c7afa5" strokeOpacity=".4" />
          <g className="pv-envelope-stripes">
            <path d="M179 320l26 16M391 320l-26 16" stroke="#d81538" strokeWidth="7" />
            <path d="M173 330l26 16M398 330l-26 16" stroke="#4e2731" strokeWidth="3" />
          </g>
          <g className="pv-seal">
            <circle cx="295" cy="301" r="54" fill="#421321" opacity=".21" transform="translate(3 8)" />
            <circle cx="295" cy="301" r="54" fill="url(#pv-crimson)" stroke="#6a2435" strokeWidth="3" />
            <circle cx="295" cy="301" r="45" fill="none" stroke="#ffe3d2" strokeOpacity=".65" strokeWidth="1.5" strokeDasharray="3 7" />
            <circle cx="295" cy="301" r="36" fill="none" stroke="#ffe3d2" strokeOpacity=".7" strokeWidth="2" />
            <g className="pv-seal-symbol" fill="none" stroke="#fff2e0" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round">
              {sealed ? (
                <path d="M276 302l12 13 27 -29" />
              ) : (
                <>
                  <rect x="278" y="296" width="34" height="28" rx="3" />
                  <path d="M284 296v-11a11 11 0 0 1 22 0v11" />
                </>
              )}
            </g>
          </g>
        </g>
        <g className="pv-vault-orbit" fill="none" stroke="#bf334d" strokeWidth="3">
          <path d="M295 74A194 194 0 0 1 489 268" />
          <path d="M295 462A194 194 0 0 1 101 268" />
        </g>
        <g className="pv-small-dot" fill="#d2153b">
          <circle cx="295" cy="74" r="6" /><circle cx="101" cy="268" r="4" /><circle cx="489" cy="268" r="4" />
        </g>
      </svg>
      <span className="pv-illustration-caption" aria-hidden="true">
        {sealed ? "DEPOSIT CONFIRMED" : sending ? "TRANSMITTING TO ASSIGNED PARTY" : armed ? "READY FOR PRIVATE TRANSFER" : "THE PRIVATE CHANNEL"}
      </span>
    </div>
  );
}

export default function FounderSubmissionForm({
  sessionId,
  partyId,
  accountCapability,
}: {
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
      // Direct browser-to-assigned-party request. The coordinator does not
      // receive an individual salary through this form.
      const response = await fetch(`${partyUrl}/sessions/${encodeURIComponent(sessionId)}/input`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${capability.trim()}`,
        },
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
    <main className={`pv-root ${armed ? "pv-root--armed" : ""} ${submitting ? "pv-root--sending" : ""} ${submitted ? "pv-root--sealed" : ""}`}>
      <div className="pv-edge-index" aria-hidden="true">VB / SECURE CHANNEL</div>
      <div className="pv-workspace">
        <section className="pv-art" aria-label="Private deposit illustration">
          <div className="pv-art-topline"><span>VEILBENCH / PRIVATE</span><span>0{validParty ? Number(partyId) + 1 : "—"} : 03</span></div>
          <VaultIllustration armed={armed} sending={submitting} sealed={submitted} partyId={validParty ? partyId : "0"} />
          <div className="pv-art-bottom"><span>01 / YOUR INPUT</span><span className="pv-art-rule"/><span>02 / SECURE DEPOSIT</span></div>
        </section>
        <section className="pv-entry" aria-label="Founder private submission">
          <div className="pv-topline"><span>ACCESS GRANTED</span><span>PARTY {validParty ? String(Number(partyId) + 1).padStart(2, "0") : "—"}</span></div>
          <div className="pv-entry-content">
            <span className="pv-eyebrow"><span className="pv-eyebrow-icon" /> PRIVATE TRANSMISSION / 01</span>
            <h1>YOUR <em>PRIVATE</em><br/>DEPOSIT.</h1>
            <p className="pv-intro">One input. One secure channel. Your salary goes directly to your assigned MPC party—not the coordinator.</p>

            {!validParty ? (
              <div className="pv-message pv-message--error" role="alert"><CircleAlert size={19}/>This link does not identify a valid assigned MPC party.</div>
            ) : submitted ? (
              <div className="pv-success" role="status" aria-live="polite">
                <span className="pv-success-icon"><Check size={32} aria-hidden="true" /></span>
                <strong>INPUT SEALED.</strong>
                <p>{message}</p>
                <span className="pv-success-small">NO FURTHER ACTION REQUIRED</span>
              </div>
            ) : (
              <form className="pv-form" onSubmit={submit}>
                <label htmlFor="pv-salary">SALARY AMOUNT <span>/ WHOLE NUMBER</span></label>
                <div className="pv-input-frame">
                  <span aria-hidden="true">01</span>
                  <input id="pv-salary" type="text" inputMode="numeric" autoComplete="off" value={salary} onChange={(event) => setSalary(event.target.value)} disabled={submitting} placeholder="Enter amount" required aria-describedby="pv-input-note" />
                </div>
                <p id="pv-input-note" className="pv-input-note">Enter a non-negative whole number. It will not be shown on the admin dashboard.</p>
                {!accountCapability && (
                  <>
                    <label htmlFor="pv-capability">ONE-TIME CAPABILITY <span>/ PRIVATE TOKEN</span></label>
                    <div className="pv-input-frame pv-input-frame--token">
                      <LockKeyhole size={19} aria-hidden="true" />
                      <input id="pv-capability" type="password" autoComplete="off" value={capability} onChange={(event) => setCapability(event.target.value)} disabled={submitting} placeholder="Paste your private token" required />
                    </div>
                  </>
                )}
                <button className="pv-send" type="submit" disabled={submitting}>
                  <span>{submitting ? "TRANSMITTING PRIVATELY…" : "SEAL & SUBMIT"}</span>
                  <ArrowRight size={24} aria-hidden="true" />
                </button>
              </form>
            )}

            {error && <div className="pv-message pv-message--error" role="alert"><CircleAlert size={19} aria-hidden="true"/><span>{error}</span></div>}
            {message && !submitted && <div className="pv-message" role="status">{message}</div>}
            <div className="pv-privacy"><ShieldCheck size={19} aria-hidden="true"/><p>Single submission only. Keep your invitation and account credentials private.</p></div>
          </div>
          <div className="pv-footer"><span>DIRECT TO YOUR ASSIGNED PARTY · NO PUBLIC INPUTS</span><span>VEILBENCH · 2026</span></div>
        </section>
      </div>
    </main>
  );
}
