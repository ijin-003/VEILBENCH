"use client";

import { useEffect, useState } from "react";
import { BookOpen, ChevronLeft, ChevronRight, ShieldCheck, X } from "lucide-react";

type Role = "welcome" | "admin" | "participant";

const steps: Record<Role, { title: string; detail: string }[]> = {
  welcome: [
    { title: "What is VEILBENCH?", detail: "Three founders compute a combined salary total and average without sending their personal salaries to the coordinator." },
    { title: "Administrator sets up a session", detail: "The administrator signs in, creates a 30-minute session and issues one private invitation for each of the three founders." },
    { title: "Founders join independently", detail: "Each founder activates their own invitation, chooses a password and signs in to their assigned MPC party." },
    { title: "Secure calculation", detail: "Once all three have submitted, the administrator starts MPyC. The coordinator receives only the combined total and average." },
  ],
  admin: [
    { title: "Create a benchmark", detail: "Use Create 30-minute session. A session expires automatically, so run your demonstration soon after creating it." },
    { title: "Invite each founder", detail: "Issue three unique usernames, one for Party 0, Party 1 and Party 2. Copy each invitation privately and send it only to its intended founder." },
    { title: "Check progress", detail: "The dashboard updates submission status automatically. You can see whether each party submitted, but never its salary." },
    { title: "Compute and explain", detail: "When 3/3 submissions are ready, choose Compute aggregate. Show the public sum and average and explain the sample secret-sharing diagram below." },
  ],
  participant: [
    { title: "Activate your own account", detail: "Use the private invitation and username given by the administrator. Set a personal password, then sign in." },
    { title: "Check your assigned party", detail: "You are assigned to exactly one MPC party. Do not share your account or invitation with other founders." },
    { title: "Submit once", detail: "Enter a whole-number salary and select Submit directly to my party. The browser sends it to your assigned party, not to the coordinator API." },
    { title: "What happens next?", detail: "After all three parties submit, the admin starts the secure computation. Only the combined total and average are published." },
  ],
};

export function GuidedTour({ role }: { role: Role }) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const current = steps[role];
  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);
  return (
    <>
      <button type="button" className="button-secondary" onClick={() => { setStep(0); setOpen(true); }} aria-label="Open guided walkthrough">
        <BookOpen className="h-4 w-4" /> Guided walkthrough
      </button>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/85 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false); }}>
          <section role="dialog" aria-modal="true" aria-label="VEILBENCH guided walkthrough" aria-describedby="veilbench-tour-description" className="w-full max-w-lg rounded-2xl border border-indigo-700 bg-slate-900 p-6 text-slate-100 shadow-2xl">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-indigo-300">Guide · Step {step + 1} of {current.length}</span>
              <button type="button" onClick={() => setOpen(false)} className="rounded-md p-2 hover:bg-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-400" aria-label="Close walkthrough"><X className="h-5 w-5" /></button>
            </div>
            <div className="mt-3 flex gap-1.5" aria-hidden="true">{current.map((item, index) => <span key={item.title} className={`h-1.5 flex-1 rounded-full ${index <= step ? "bg-indigo-400" : "bg-slate-700"}`} />)}</div>
            <h2 className="mt-6 text-2xl font-bold">{current[step].title}</h2>
            <p id="veilbench-tour-description" className="mt-3 leading-relaxed text-slate-300">{current[step].detail}</p>
            <div className="mt-7 flex items-center justify-between gap-3">
              <button type="button" className="button-secondary" disabled={step === 0} onClick={() => setStep((value) => Math.max(0, value - 1))}><ChevronLeft className="h-4 w-4" /> Back</button>
              <button type="button" className="button-primary" onClick={() => { if (step === current.length - 1) setOpen(false); else setStep((value) => value + 1); }}>
                {step === current.length - 1 ? "Finish" : "Next"} {step < current.length - 1 && <ChevronRight className="h-4 w-4" />}
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}

const mathStages = [
  {
    label: "1 · Private inputs",
    text: "Example only: the three fictional salaries are 50, 70 and 60. Real salaries are never filled into this illustration.",
    data: ["Founder A · 50", "Founder B · 70", "Founder C · 60"],
  },
  {
    label: "2 · Shamir shares",
    text: "For illustration, use prime 1009 and random example slopes 17, 23 and 31. Each founder evaluates a degree-one polynomial at x = 1, 2 and 3. A party receives only its own column.",
    data: ["Party 0 · 67, 93, 91", "Party 1 · 84, 116, 122", "Party 2 · 101, 139, 153"],
  },
  {
    label: "3 · Sum shared values",
    text: "Each party adds the shares it holds modulo 1009, without reconstructing anyone's salary.",
    data: ["Party 0 sum · 251", "Party 1 sum · 322", "Party 2 sum · 393"],
  },
  {
    label: "4 · Reconstruct total",
    text: "With threshold 1, any two aggregated shares are mathematically enough: Lagrange interpolation at zero gives (2 × 251 − 322) mod 1009 = 180. Only the aggregate is reconstructed.",
    data: ["Public aggregate · 180"],
  },
  {
    label: "5 · Publish average",
    text: "Divide the public aggregate by three founders. No individual salary is published.",
    data: ["180 ÷ 3 = 60"],
  },
];

export function ProtocolWalkthrough() {
  const [active, setActive] = useState(0);
  const stage = mathStages[active];
  return (
    <section className="rounded-xl border border-indigo-900 bg-slate-900/75 p-5 text-slate-100" aria-labelledby="mpc-explainer-title">
      <div className="flex items-center gap-2 text-indigo-300"><ShieldCheck className="h-5 w-5" /><h2 id="mpc-explainer-title" className="font-semibold">How MPC protects salaries</h2></div>
      <p className="mt-2 text-sm text-slate-300">Explore the five steps of Shamir-based secure summation. All numbers below are <strong>synthetic teaching examples</strong>, not live inputs, live shares or production protocol parameters.</p>
      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-5" role="group" aria-label="Protocol explanation steps">
        {mathStages.map((item, index) => <button key={item.label} type="button" onClick={() => setActive(index)} aria-pressed={active === index} className={`rounded-lg border p-2 text-left text-xs font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-400 ${active === index ? "border-indigo-400 bg-indigo-900/50 text-white" : "border-slate-700 bg-slate-950 text-slate-300 hover:border-indigo-600"}`}>{item.label}</button>)}
      </div>
      <div className="mt-4 rounded-lg border border-slate-700 bg-slate-950 p-4" aria-live="polite">
        <h3 className="font-semibold text-indigo-200">{stage.label}</h3>
        <p className="mt-2 text-sm leading-relaxed text-slate-300">{stage.text}</p>
        <div className="mt-4 grid gap-2 sm:grid-cols-3">{stage.data.map((value) => <div key={value} className="rounded-md border border-slate-700 bg-slate-900 px-3 py-3 text-center font-mono text-sm text-emerald-300">{value}</div>)}</div>
      </div>
      <p className="mt-3 text-xs leading-relaxed text-amber-200">Privacy boundary: this is a three-party, threshold-1 demonstration. One share does not reconstruct a secret; two colluding parties can. All three processes currently run on one shared hosting service, so separate infrastructure trust is not claimed.</p>
    </section>
  );
}
