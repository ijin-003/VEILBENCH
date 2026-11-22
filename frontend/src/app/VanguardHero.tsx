
"use client";

import { useEffect, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import {
  ArrowRight,
  Home,
  Info,
  Layers3,
  ShieldCheck,
  X,
} from "lucide-react";

type Props = {
  onStart: () => void;
};

type Panel = "process" | "security" | "about" | null;

export default function VanguardHero({ onStart }: Props) {
  const [panel, setPanel] = useState<Panel>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const frameRef = useRef<number | null>(null);

  const closePanel = () => setPanel(null);

  function handlePointerMove(event: ReactPointerEvent<HTMLElement>) {
    if (event.pointerType !== "mouse" || panel) return;

    const bounds = event.currentTarget.getBoundingClientRect();

    const x =
      ((event.clientX - bounds.left) / bounds.width - 0.5) * 2;

    const y =
      ((event.clientY - bounds.top) / bounds.height - 0.5) * 2;

    if (frameRef.current !== null) {
      cancelAnimationFrame(frameRef.current);
    }

    frameRef.current = requestAnimationFrame(() => {
      if (!stageRef.current) return;

      stageRef.current.style.setProperty("--vb-x", `${x * 9}px`);
      stageRef.current.style.setProperty("--vb-y", `${y * 7}px`);

      frameRef.current = null;
    });
  }

  function resetPointer() {
    if (frameRef.current !== null) {
      cancelAnimationFrame(frameRef.current);
      frameRef.current = null;
    }

    stageRef.current?.style.setProperty("--vb-x", "0px");
    stageRef.current?.style.setProperty("--vb-y", "0px");
  }

  useEffect(() => {
    if (!panel) return;

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setPanel(null);
    }

    window.addEventListener("keydown", handleEscape);

    return () => {
      window.removeEventListener("keydown", handleEscape);
    };
  }, [panel]);

  useEffect(() => {
    return () => {
      if (frameRef.current !== null) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, []);

  return (
    <main
      className="vanguard"
      onPointerMove={handlePointerMove}
      onPointerLeave={resetPointer}
    >
      {/* Cinematic stage - artwork and buttons stay aligned */}
      <div ref={stageRef} className="vanguard-stage">

        {/* Main illustration */}
        <div className="vanguard-art" aria-hidden="true" />

        {/* Animated atmosphere */}
        <div className="vanguard-light" aria-hidden="true" />
        <div className="vanguard-grain" aria-hidden="true" />

        {/* Navigation */}
        <nav
          className="vanguard-nav"
          aria-label="Main navigation"
        >
          <button
            type="button"
            className="vanguard-nav-button"
            aria-label="Home"
            title="Home"
            onClick={closePanel}
          >
            <Home aria-hidden="true" />
          </button>

          <button
            type="button"
            className="vanguard-nav-button"
            aria-label="How VEILBENCH works"
            title="How it works"
            onClick={() => setPanel("process")}
          >
            <Layers3 aria-hidden="true" />
          </button>

          <button
            type="button"
            className="vanguard-nav-button"
            aria-label="Security information"
            title="Security"
            onClick={() => setPanel("security")}
          >
            <ShieldCheck aria-hidden="true" />
          </button>

          <button
            type="button"
            className="vanguard-nav-button"
            aria-label="About VEILBENCH"
            title="About"
            onClick={() => setPanel("about")}
          >
            <Info aria-hidden="true" />
          </button>
        </nav>

        {/* Desktop START button */}
        <button
          type="button"
          className="vanguard-start"
          onClick={onStart}
          aria-label="Start VEILBENCH - sign in or activate account"
        >
          <span className="vanguard-start-mobile">
            START
            <ArrowRight aria-hidden="true" size={23} />
          </span>
        </button>

        {/* Mobile content */}
        <div className="vanguard-mobile-content">
          <div className="vanguard-mobile-kicker">
            SECURE MULTIPARTY COMPUTATION
          </div>

          <h1>VEILBENCH</h1>

          <p>PRIVATE INPUTS. COLLECTIVE INSIGHT.</p>

          <button
            type="button"
            className="vanguard-mobile-cta"
            onClick={onStart}
          >
            ENTER SYSTEM
            <ArrowRight aria-hidden="true" size={22} />
          </button>
        </div>
      </div>

      {/* Information overlay */}
      {panel && (
        <div
          className="vanguard-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closePanel();
            }
          }}
        >
          <section
            className="vanguard-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="vanguard-panel-title"
          >
            <div className="vanguard-panel-top">
              <span>
                VEILBENCH // SYSTEM INFORMATION
              </span>

              <button
                type="button"
                onClick={closePanel}
                aria-label="Close information panel"
              >
                <X size={23} />
              </button>
            </div>

            {panel === "process" && (
              <>
                <span className="vanguard-panel-number">
                  01 / PROTOCOL
                </span>

                <h2 id="vanguard-panel-title">
                  HOW IT WORKS
                </h2>

                <p>
                  Three founders contribute private salary inputs.
                  Each founder submits directly to an assigned MPC
                  party. Once all submissions are ready, the
                  administrator starts the secure computation.
                </p>

                <div className="vanguard-panel-steps">
                  <span>01 — CREATE SESSION</span>
                  <span>02 — SUBMIT PRIVATELY</span>
                  <span>03 — COMPUTE AGGREGATE</span>
                </div>
              </>
            )}

            {panel === "security" && (
              <>
                <span className="vanguard-panel-number">
                  02 / PRIVACY
                </span>

                <h2 id="vanguard-panel-title">
                  BUILT FOR PRIVACY
                </h2>

                <p>
                  VEILBENCH uses secure multiparty computation
                  to calculate a combined salary total and average.
                  Individual salary values are not displayed in
                  the administrator's results.
                </p>

                <p>
                  This demonstration uses shared hosting
                  infrastructure. It does not provide independent
                  organizational control of each MPC party.
                </p>
              </>
            )}

            {panel === "about" && (
              <>
                <span className="vanguard-panel-number">
                  03 / PROJECT
                </span>

                <h2 id="vanguard-panel-title">
                  VEILBENCH
                </h2>

                <p>
                  A privacy-preserving benchmarking demonstration
                  powered by secure multiparty computation.
                </p>

                <p>
                  Designed to show how multiple participants can
                  calculate collective statistics without publishing
                  their individual inputs.
                </p>
              </>
            )}

            <button
              type="button"
              className="vanguard-panel-enter"
              onClick={onStart}
            >
              ENTER VEILBENCH
              <ArrowRight size={21} aria-hidden="true" />
            </button>
          </section>
        </div>
      )}
    </main>
  );
}
