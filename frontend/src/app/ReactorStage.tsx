"use client";

import { useEffect, useRef, useState } from "react";

/** Visual state only: salary data and tokens never reach this component. */
type Props = { submitted: ReadonlySet<number>; stage: string };
type CapsulePhase = "floating" | "sealing" | "traveling" | "docked";
const IDS = [0, 1, 2] as const;

function Capsule({ id, received, initial }: { id: number; received: boolean; initial: boolean }) {
  const [phase, setPhase] = useState<CapsulePhase>(received ? "docked" : "floating");
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const lastReceived = useRef(received);

  useEffect(() => {
    // The initial snapshot is rendered already docked so reloading a page
    // cannot falsely imply a new submission has just happened.
    if (initial) {
      setPhase(received ? "docked" : "floating");
      lastReceived.current = received;
      return;
    }
    if (received && !lastReceived.current) {
      setPhase("sealing");
      const a = setTimeout(() => setPhase("traveling"), 700);
      const b = setTimeout(() => setPhase("docked"), 2200);
      timers.current.push(a, b);
    } else if (!received && lastReceived.current) {
      setPhase("floating");
    }
    lastReceived.current = received;
    return () => {
      timers.current.forEach(clearTimeout);
      timers.current = [];
    };
  }, [received, initial]);

  return (
    <div className={`v5-capsule-position v5-capsule-${id + 1} v5-phase-${phase}`}
      role="listitem" aria-label={`Founder ${id + 1}: ${received ? "submission received" : "awaiting submission"}`}>
      <div className="v5-capsule-flight">
        <div className="v5-capsule-float">
          <div className="v5-capsule-shell" aria-hidden="true">
            <span className="v5-capsule-cap v5-capsule-cap--top" />
            <span className="v5-capsule-glass"><span className="v5-capsule-liquid"/><span className="v5-capsule-shine"/><b>0{id + 1}</b></span>
            <span className="v5-capsule-cap v5-capsule-cap--bottom" />
            <span className="v5-capsule-lock">◆</span>
          </div>
        </div>
      </div>
      <span className="v5-capsule-id" aria-hidden="true">0{id + 1}</span>
    </div>
  );
}

export default function ReactorStage({ submitted, stage }: Props) {
  const count = IDS.filter(id => submitted.has(id)).length;
  const computing = stage === "computing";
  const completed = stage === "completed";
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  // First client render uses the server's snapshot; later changes animate.
  const [firstSnapshot] = useState(() => IDS.map(id => submitted.has(id)));

  return (
    <div className={`v5-scene ${computing ? "v5-scene--computing" : ""} ${completed ? "v5-scene--completed" : ""} ${count === 3 ? "v5-scene--ready" : ""}`}>
      <div className="v5-scene-slasher" aria-hidden="true" />
      <div className="v5-scene-orbit v5-scene-orbit--a" aria-hidden="true" />
      <div className="v5-scene-orbit v5-scene-orbit--b" aria-hidden="true" />

      <div className="v5-machine" aria-hidden="true">
        <svg viewBox="0 0 360 520" preserveAspectRatio="xMidYMid meet">
          <defs>
            <linearGradient id="v5-body" x1="0" x2="1" y1="0" y2="0">
              <stop offset="0" stopColor="#d5c9b5"/><stop offset=".27" stopColor="#fff8e9"/><stop offset=".7" stopColor="#eee1cb"/><stop offset="1" stopColor="#9f9082"/>
            </linearGradient>
            <linearGradient id="v5-core" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#141112"/><stop offset=".52" stopColor="#b60924"/><stop offset="1" stopColor="#190f14"/>
            </linearGradient>
          </defs>
          <ellipse cx="180" cy="474" rx="150" ry="22" fill="#171013" opacity=".15"/>
          <path d="M98 438L125 125L159 82H210L243 125L268 438L234 474H124Z" fill="#111012" stroke="#120e0f" strokeWidth="5"/>
          <path d="M116 429L138 130L165 99H195L222 129L245 430L223 448H139Z" fill="url(#v5-body)" stroke="#130e10" strokeWidth="6"/>
          <path d="M155 107H205L216 135L210 396H150L144 135Z" fill="url(#v5-core)" stroke="#141012" strokeWidth="5"/>
          <path d="M174 139H186V394H174Z" fill="#ff2a3d" className="v5-machine-beam" opacity=".5"/>
          <path d="M117 174L146 148L152 379L129 415Z" fill="#fdf6e8" stroke="#161115" strokeWidth="3"/>
          <path d="M218 148L243 175L232 416L209 377Z" fill="#f5e7d0" stroke="#161115" strokeWidth="3"/>
          <path d="M113 432H247L282 475H78Z" fill="#111012" stroke="#fff8eb" strokeWidth="5"/>
          <path d="M134 440H226L244 463H115Z" fill="#e9dccc"/>
          <path d="M161 112L180 88L199 112Z" fill="#0d0b0d"/>
          <path d="M180 242l14 22-14 23-14-23Z" fill="#fff0de" className="v5-machine-symbol"/>
          <path d="M180 253l7 11-7 12-7-12Z" fill="#ee102f"/>
          <path d="M110 325H141M220 325H250" stroke="#ef1032" strokeWidth="5"/>
          <path d="M142 397H218" stroke="#fff1df" strokeWidth="7"/>
        </svg>
        <div className="v5-machine-halo" />
        <div className="v5-machine-platform" />
      </div>

      <div className="v5-docks" aria-label={`${count} out of 3 founder submissions received`}>
        {IDS.map(id => <div key={id} className={`v5-dock v5-dock-${id + 1} ${submitted.has(id) ? "v5-dock--active" : ""}`}>
          <span className="v5-dock-light"/><span className="v5-dock-num">0{id + 1}</span>
        </div>)}
      </div>
      <div className="v5-floating-capsules" role="list" aria-label="Founder capsules">
        {IDS.map(id => <Capsule key={id} id={id} received={submitted.has(id)} initial={!mounted && firstSnapshot[id]} />)}
      </div>
      <div className="v5-scene-count" aria-live="polite"><strong>{count}<span> / 03</span></strong><small>CAPSULES SECURED</small></div>
    </div>
  );
}
