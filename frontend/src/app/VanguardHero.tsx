"use client";

import { useEffect, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import { ArrowRight, Home, Info, Layers3, ShieldCheck, X } from "lucide-react";

type Props = { onStart: () => void };
type Panel = "process" | "security" | "about";
type Scene = "home" | Panel | "start";

const scenes: Record<Exclude<Scene, "home">, { number: string; label: string; title: string; subtitle: string }> = {
  process: { number: "01", label: "THE PROTOCOL", title: "THREE INPUTS.", subtitle: "ONE COLLECTIVE RESULT." },
  security: { number: "02", label: "THE GUARANTEE", title: "PRIVATE BY", subtitle: "DESIGN. NOT BY PROMISE." },
  about: { number: "03", label: "THE PROJECT", title: "MEET THE", subtitle: "BENCHMARK." },
  start: { number: "00", label: "ENTER THE SYSTEM", title: "READY TO", subtitle: "BEGIN?" },
};

/** Decorative SVG overlays are vector paths, not copies of the PNG artwork. */
function MotionGraphics({ scene }: { scene: Scene }) {
  return (
    <div className="vanguard-graphics" aria-hidden="true">
      <svg className="vanguard-vector" viewBox="0 0 1672 941" preserveAspectRatio="none">
        <defs>
          <pattern id="vb-halftone" width="13" height="13" patternUnits="userSpaceOnUse">
            <circle cx="2" cy="2" r="1.5" fill="#f8ebd6" opacity="0.45" />
          </pattern>
          <clipPath id="vb-left-clip"><path d="M0 170 H856 L740 566 H0 Z" /></clipPath>
        </defs>
        <g className="vb-vector-idle">
          <path className="vb-idle-slash" d="M965 -55 L996 -55 L533 991 L508 991 Z" fill="#f4e7d0" />
          <path className="vb-idle-slash vb-idle-slash-second" d="M1136 -40 L1151 -40 L746 950 L725 950 Z" fill="#e50922" />
          <path d="M0 0 H1672" stroke="#e50922" opacity=".20" strokeWidth="2" />
        </g>
        <g className="vb-scene-vectors" data-active={scene !== "home"}>
          {/* Covers the embedded headline only while a hover scene is active. */}
          <path className="vb-scene-ink" d="M0 200 L855 183 L755 505 L0 565 Z" fill="#0b090a" />
          <path className="vb-scene-stripe" d="M0 201 L272 201 L87 568 L0 568 Z" fill="var(--vb-scene-accent)" />
          <path className="vb-scene-panel" d="M10 273 L774 234 L697 486 L0 507 Z" fill="var(--vb-scene-panel)" />
          <path className="vb-scene-hatch" d="M0 489 L635 457 L608 524 L0 544 Z" fill="url(#vb-halftone)" clipPath="url(#vb-left-clip)" opacity=".45" />
          <path className="vb-scene-stroke" d="M72 232 L814 196" stroke="var(--vb-scene-accent)" strokeWidth="5" />
          <path className="vb-scene-stroke vb-scene-stroke-second" d="M28 528 L650 491" stroke="#f8ebd6" strokeWidth="2" />
          <path className="vb-scene-arrow" d="M683 518 H782 L753 489 M782 518 L753 547" stroke="var(--vb-scene-accent)" strokeWidth="8" fill="none" />
        </g>
      </svg>
      <div className="vanguard-scene-copy" data-active={scene !== "home"}>
        {scene !== "home" && (
          <div key={scene} className="vanguard-scene-copy-inner">
            <span className="vb-scene-eyebrow">{scenes[scene].number} / {scenes[scene].label}</span>
            <strong>{scenes[scene].title}</strong>
            <span className="vb-scene-subtitle">{scenes[scene].subtitle}</span>
          </div>
        )}
      </div>
      <div className="vanguard-motion-index" data-active={scene !== "home"}>
        <span>{scene === "home" ? "EXPLORE" : scenes[scene].label}</span>
        <i /><i /><i />
      </div>
    </div>
  );
}

export default function VanguardHero({ onStart }: Props) {
  const [panel, setPanel] = useState<Panel | null>(null);
  const [hovered, setHovered] = useState<Scene | null>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const frameRef = useRef<number | null>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);
  const scene = panel ?? hovered ?? "home";

  function openPanel(next: Panel) {
    previousFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setHovered(null);
    setPanel(next);
  }

  function closePanel() {
    setPanel(null);
    setHovered(null);
    previousFocus.current?.focus();
  }

  function handlePointerMove(event: ReactPointerEvent<HTMLElement>) {
    if (event.pointerType !== "mouse" || panel) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - bounds.left) / bounds.width - 0.5) * 2;
    const y = ((event.clientY - bounds.top) / bounds.height - 0.5) * 2;
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    frameRef.current = requestAnimationFrame(() => {
      stageRef.current?.style.setProperty("--vb-x", `${x * 8}px`);
      stageRef.current?.style.setProperty("--vb-y", `${y * 6}px`);
      frameRef.current = null;
    });
  }

  function resetPointer() {
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    frameRef.current = null;
    stageRef.current?.style.setProperty("--vb-x", "0px");
    stageRef.current?.style.setProperty("--vb-y", "0px");
    setHovered(null);
  }

  useEffect(() => {
    if (!panel) return;
    closeRef.current?.focus();
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setPanel(null);
        setHovered(null);
        previousFocus.current?.focus();
      }
      if (event.key !== "Tab") return;
      const dialog = closeRef.current?.closest("[role=dialog]");
      const buttons = Array.from(dialog?.querySelectorAll<HTMLButtonElement>("button:not(:disabled)") ?? []);
      if (!buttons.length) return;
      const first = buttons[0];
      const last = buttons[buttons.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first.focus();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [panel]);

  useEffect(() => () => {
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
  }, []);

  return (
    <main className="vanguard" onPointerMove={handlePointerMove} onPointerLeave={resetPointer}>
      <div ref={stageRef} className="vanguard-stage" data-scene={scene}>
        <div className="vanguard-art" aria-hidden="true" />
        <div className="vanguard-light" aria-hidden="true" />
        <div className="vanguard-grain" aria-hidden="true" />
        <MotionGraphics scene={scene} />

        <nav className="vanguard-nav" aria-label="Main navigation">
          <button type="button" className="vanguard-nav-button" aria-label="Home" title="Home"
            onMouseEnter={() => setHovered("home")} onFocus={() => setHovered("home")}
            onMouseLeave={() => setHovered(null)} onClick={() => { setPanel(null); setHovered(null); }}>
            <Home aria-hidden="true" />
          </button>
          <button type="button" className="vanguard-nav-button" aria-label="How VEILBENCH works" title="How it works"
            onMouseEnter={() => setHovered("process")} onFocus={() => setHovered("process")}
            onMouseLeave={() => setHovered(null)} onClick={() => openPanel("process")}>
            <Layers3 aria-hidden="true" />
          </button>
          <button type="button" className="vanguard-nav-button" aria-label="Security information" title="Security"
            onMouseEnter={() => setHovered("security")} onFocus={() => setHovered("security")}
            onMouseLeave={() => setHovered(null)} onClick={() => openPanel("security")}>
            <ShieldCheck aria-hidden="true" />
          </button>
          <button type="button" className="vanguard-nav-button" aria-label="About VEILBENCH" title="About"
            onMouseEnter={() => setHovered("about")} onFocus={() => setHovered("about")}
            onMouseLeave={() => setHovered(null)} onClick={() => openPanel("about")}>
            <Info aria-hidden="true" />
          </button>
        </nav>

        <button type="button" className="vanguard-start" onClick={onStart}
          onMouseEnter={() => setHovered("start")} onMouseLeave={() => setHovered(null)}
          onFocus={() => setHovered("start")}
          aria-label="Start VEILBENCH - sign in or activate account">
          <span className="vanguard-start-orbit" aria-hidden="true" />
          <span className="vanguard-start-mobile">START <ArrowRight aria-hidden="true" size={23} /></span>
        </button>

        <div className="vanguard-mobile-content">
          <div className="vanguard-mobile-kicker">SECURE MULTIPARTY COMPUTATION</div>
          <h1>VEILBENCH</h1>
          <p>PRIVATE INPUTS. COLLECTIVE INSIGHT.</p>
          <button type="button" className="vanguard-mobile-cta" onClick={onStart}>
            ENTER SYSTEM <ArrowRight aria-hidden="true" size={22} />
          </button>
        </div>
      </div>

      {panel && (
        <div className="vanguard-overlay" onMouseDown={(event) => {
          if (event.target === event.currentTarget) closePanel();
        }}>
          <section className="vanguard-panel" role="dialog" aria-modal="true" aria-labelledby="vanguard-panel-title">
            <div className="vanguard-panel-top">
              <span>VEILBENCH // SYSTEM INFORMATION</span>
              <button ref={closeRef} type="button" onClick={closePanel} aria-label="Close information panel"><X size={23} /></button>
            </div>
            {panel === "process" && <>
              <span className="vanguard-panel-number">01 / PROTOCOL</span>
              <h2 id="vanguard-panel-title">HOW IT WORKS</h2>
              <p>Three founders contribute private salary inputs. Each founder submits directly to an assigned MPC party. Once all submissions are ready, the administrator starts the secure computation.</p>
              <div className="vanguard-panel-steps"><span>01 — CREATE SESSION</span><span>02 — SUBMIT PRIVATELY</span><span>03 — COMPUTE AGGREGATE</span></div>
            </>}
            {panel === "security" && <>
              <span className="vanguard-panel-number">02 / PRIVACY</span>
              <h2 id="vanguard-panel-title">BUILT FOR PRIVACY</h2>
              <p>VEILBENCH uses secure multiparty computation to calculate a combined salary total and average. Individual salary values are not displayed in the administrator&apos;s results.</p>
              <p>This demonstration uses shared hosting infrastructure. It does not provide independent organizational control of each MPC party.</p>
            </>}
            {panel === "about" && <>
              <span className="vanguard-panel-number">03 / PROJECT</span>
              <h2 id="vanguard-panel-title">VEILBENCH</h2>
              <p>A privacy-preserving benchmarking demonstration powered by secure multiparty computation.</p>
              <p>Designed to show how multiple participants can calculate collective statistics without publishing their individual inputs.</p>
            </>}
            <button type="button" className="vanguard-panel-enter" onClick={onStart}>
              ENTER VEILBENCH <ArrowRight size={21} aria-hidden="true" />
            </button>
          </section>
        </div>
      )}
    </main>
  );
}
