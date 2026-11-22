"use client";

import { FormEvent, useMemo, useState } from "react";
import { CheckCircle2, Lock, ShieldCheck } from "lucide-react";

const partyUrls: Record<string, string | undefined> = {
  "0": process.env.NEXT_PUBLIC_PARTY_0_URL,
  "1": process.env.NEXT_PUBLIC_PARTY_1_URL,
  "2": process.env.NEXT_PUBLIC_PARTY_2_URL,
};

export default function FounderSubmissionForm({
  sessionId,
  partyId,
}: {
  sessionId: string;
  partyId: string;
}) {
  const [salary, setSalary] = useState("");
  const [capability, setCapability] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const validParty = ["0", "1", "2"].includes(partyId);
  const partyUrl = useMemo(() => partyUrls[partyId]?.replace(/\/+$/, ""), [partyId]);

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
      // This browser request goes directly to the assigned party URL. The salary
      // is never posted to the coordinator API or stored in this frontend.
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
      if (!response.ok) {
        throw new Error(data.detail || `Submission failed with HTTP ${response.status}`);
      }
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

  if (!validParty) {
    return (
      <main className="min-h-screen bg-slate-950 p-6 text-slate-100">
        <div className="mx-auto max-w-lg rounded-xl border border-rose-900 bg-slate-900/70 p-6">
          <h1 className="text-xl font-bold text-rose-300">Invalid founder invitation</h1>
          <p className="mt-3 text-sm text-slate-300">This link does not identify one of the three assigned MPC parties.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 p-6 text-slate-100">
      <div className="mx-auto max-w-lg rounded-xl border border-slate-800 bg-slate-900/70 p-6">
        <div className="flex items-center gap-2 text-indigo-300">
          <Lock className="h-5 w-5" />
          <h1 className="text-xl font-bold">Founder {Number(partyId) + 1} private submission</h1>
        </div>
        <p className="mt-3 text-sm text-slate-400">
          Your salary is sent directly from this browser to your assigned MPC party. It is not sent to the
          coordinator. Use only the one-time capability issued for this invitation.
        </p>
        <div className="mt-4 flex items-start gap-2 rounded-md border border-indigo-900 bg-indigo-950/40 p-3 text-xs text-indigo-200">
          <ShieldCheck className="h-4 w-4 shrink-0" />
          <p>Keep your capability private. It is single-use and should not be shared with another founder.</p>
        </div>

        {submitted ? (
          <div className="mt-5 rounded-lg border border-emerald-800 bg-emerald-950/40 p-4">
            <p className="flex items-start gap-2 text-sm text-emerald-300">
              <CheckCircle2 className="h-5 w-5 shrink-0" /> {message}
            </p>
          </div>
        ) : (
          <form className="mt-5 space-y-4" onSubmit={submit}>
            <label className="block text-sm">
              Salary
              <input
                className="input mt-1 w-full"
                type="text"
                inputMode="numeric"
                autoComplete="off"
                value={salary}
                onChange={(event) => setSalary(event.target.value)}
                disabled={submitting}
                aria-label="Salary"
              />
            </label>
            <label className="block text-sm">
              One-time founder capability
              <input
                className="input mt-1 w-full"
                type="password"
                autoComplete="off"
                value={capability}
                onChange={(event) => setCapability(event.target.value)}
                disabled={submitting}
                aria-label="Founder capability"
              />
            </label>
            <button className="button-primary w-full" type="submit" disabled={submitting}>
              {submitting ? "Submitting privately…" : "Submit directly to my party"}
            </button>
          </form>
        )}
        {message && !submitted && <p className="mt-4 text-sm text-emerald-300">{message}</p>}
        {error && <p role="alert" className="mt-4 text-sm text-rose-300">{error}</p>}
      </div>
    </main>
  );
}
