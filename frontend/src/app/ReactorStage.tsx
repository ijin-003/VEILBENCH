"use client";

import { useEffect, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import Image from "next/image";
import "./reactor-v7.css";

/** This component receives submission status only, never salaries or tokens. */
type Props = { submitted: ReadonlySet<number>; stage: string };
type CapsulePhase = "floating" | "sealing" | "inserting" | "docked";
type SceneFocus = "ambient" | "machine" | "capsule";
const PARTY_IDS = [0, 1, 2] as const;

function Capsule({ id, received }: { id: number; received: boolean }) {
  // Snapshot on first mount: already-submitted parties start in the dock.
  const [phase, setPhase] = useState<CapsulePhase>(() => received ? "docked" : "floating");
  const previous = useRef(received);
  useEffect(() => {
    let sealTimer: ReturnType<typeof setTimeout> | undefined;
    let dockTimer: ReturnType<typeof setTimeout> | undefined;
    if (received && !previous.current) {
      setPhase("sealing");
      sealTimer = setTimeout(() => setPhase("inserting"), 650);
      dockTimer = setTimeout(() => setPhase("docked"), 2050);
    } else if (!received && previous.current) {
      setPhase("floating");
    }
    previous.current = received;
    return () => {
      if (sealTimer) clearTimeout(sealTimer);
      if (dockTimer) clearTimeout(dockTimer);
    };
  }, [received]);

  return (
    <div className={`rv7-capsule rv7-capsule-${id + 1} rv7-capsule--${phase}`}
      role="listitem" aria-label={`Founder ${id + 1}: ${received ? "submission secured" : "waiting for input"}`}>
      <div className="rv7-capsule-flight">
        <div className="rv7-capsule-hover">
          <div className="rv7-capsule-illustration" aria-hidden="true">
            <span className="rv7-cap rv7-cap--top" />
            <span className="rv7-glass">
              <span className="rv7-energy" />
              <span className="rv7-shine" />
              <span className="rv7-capsule-label">0{id + 1}</span>
            </span>
            <span className="rv7-cap rv7-cap--bottom" />
            <span className="rv7-seal-mark" />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ReactorStage({ submitted, stage }: Props) {
  const sceneRef = useRef<HTMLDivElement>(null);
  const [focus, setFocus] = useState<SceneFocus>("ambient");
  const count = PARTY_IDS.filter(id => submitted.has(id)).length;
  const computing = stage === "computing";
  const complete = stage === "completed";
  const ready = count === 3 && !computing && !complete;

  function move(event: ReactPointerEvent<HTMLDivElement>) {
    if (event.pointerType !== "mouse") return;
    const el = sceneRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    el.style.setProperty("--rv7-mx", `${((x - .5) * 18).toFixed(2)}px`);
    el.style.setProperty("--rv7-my", `${((y - .5) * 12).toFixed(2)}px`);
    el.style.setProperty("--rv7-pointer-x", `${(x * 100).toFixed(1)}%`);
    el.style.setProperty("--rv7-pointer-y", `${(y * 100).toFixed(1)}%`);
    const nearCapsule = (x < .31 && y < .72) || (x > .73 && y < .70);
    setFocus(old => {
      const next = nearCapsule ? "capsule" : x > .34 && x < .73 ? "machine" : "ambient";
      return next === old ? old : next;
    });
  }
  function leave() {
    setFocus("ambient");
    sceneRef.current?.style.setProperty("--rv7-mx", "0px");
    sceneRef.current?.style.setProperty("--rv7-my", "0px");
  }

  return (
    <div ref={sceneRef} className={`rv7-scene rv7-focus-${focus} ${ready ? "rv7-ready" : ""} ${computing ? "rv7-computing" : ""} ${complete ? "rv7-complete" : ""}`}
      onPointerMove={move} onPointerLeave={leave}>
      <div className="rv7-pointer-light" aria-hidden="true" />
      <div className="rv7-paper-slash rv7-paper-slash--one" aria-hidden="true" />
      <div className="rv7-paper-slash rv7-paper-slash--two" aria-hidden="true" />
      <div className="rv7-stroke rv7-stroke--one" aria-hidden="true" />
      <div className="rv7-stroke rv7-stroke--two" aria-hidden="true" />
      <div className="rv7-halo" aria-hidden="true" />
      <div className="rv7-orbit rv7-orbit--one" aria-hidden="true" />
      <div className="rv7-orbit rv7-orbit--two" aria-hidden="true" />

      <div className="rv7-monolith" aria-hidden="true">
        <Image className="rv7-monolith-image" src="/images/reactor-monolith-v7.png" alt="" fill priority sizes="(max-width: 750px) 65vw, 48vw" />
        <div className="rv7-core-ring" />
        <div className="rv7-docks">
          {PARTY_IDS.map(id => <div key={id} className={`rv7-dock rv7-dock-${id + 1} ${submitted.has(id) ? "rv7-dock--active" : ""}`}><i /><span>0{id + 1}</span></div>)}
        </div>
      </div>

      <div className="rv7-capsules" role="list" aria-label="Three private submission capsules">
        {PARTY_IDS.map(id => <Capsule key={id} id={id} received={submitted.has(id)} />)}
      </div>
      <div className="rv7-count" aria-live="polite"><b>{count}<span> / 03</span></b><small>INPUTS SECURED</small></div>
      <div className="rv7-mark" aria-hidden="true">///</div>
    </div>
  );
}
