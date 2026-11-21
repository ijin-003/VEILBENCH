"use client";

import { FormEvent, useMemo, useState } from "react";
import { CheckCircle2, Lock } from "lucide-react";

const partyUrls: Record<string, string | undefined> = {
  "0": process.env.NEXT_PUBLIC_PARTY_0_URL,
  "1": process.env.NEXT_PUBLIC_PARTY_1_URL,
  "2": process.env.NEXT_PUBLIC_PARTY_2_URL,
};

export default function FounderSubmissionPage({ params }: { params: { sessionId: string; partyId: string } }) {
  const [salary, setSalary] = useState("");
  const [capability, setCapability] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const partyUrl = useMemo(() => partyUrls[params.partyId], [params.partyId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    const amount = Number(salary);
    if (!Number.isSafeInteger(amount) || amount < 0) {
      setError("Enter a whole, non-negative salary amount.");
      return;
    }
    if (!partyUrl) {
      setError("This submission page has an invalid party configuration.");
      return;
    }
    try {
      // This browser request goes directly to the party URL. It never passes
      // through the coordinator backend or its session database.
      const response = await fetch(`${partyUrl}/sessions/${params.sessionId}/input`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${capability}` },
        body: JSON.stringify({ salary: amount }),
        credentials: "omit",
        referrerPolicy: "no-referrer",
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Submission failed with HTTP ${response.status}`);
      setSalary("");
      setCapability("");
      setMessage("Private input accepted by the assigned MPC party. You may close this page.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Private submission failed");
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 p-6 text-slate-100">
      <div className="mx-auto max-w-lg rounded-xl border border-slate-800 bg-slate-900/70 p-6">
        <div className="flex items-center gap-2 text-indigo-300"><Lock className="h-5 w-5" /><h1 className="text-xl font-bold">Founder {Number(params.partyId) + 1} private submission</h1></div>
        <p className="mt-3 text-sm text-slate-400">Your value is posted directly to your assigned HTTPS MPC party. Do not enter another founder&apos;s capability.</p>
        <form className="mt-5 space-y-4" onSubmit={submit}>
          <label className="block text-sm">Salary<input className="input mt-1 w-full" inputMode="numeric" autoComplete="off" value={salary} onChange={(event) => setSalary(event.target.value)} /></label>
          <label className="block text-sm">Founder capability<input className="input mt-1 w-full" type="password" autoComplete="off" value={capability} onChange={(event) => setCapability(event.target.value)} /></label>
          <button className="button-primary w-full" type="submit">Submit directly to party</button>
        </form>
        {message && <p className="mt-4 flex gap-2 text-sm text-emerald-300"><CheckCircle2 className="h-5 w-5 shrink-0" />{message}</p>}
        {error && <p role="alert" className="mt-4 text-sm text-rose-300">{error}</p>}
      </div>
    </main>
  );
}
