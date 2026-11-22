
"use client";

import { useState } from "react";
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

    const closePanel = () => setPanel(null);

    return (
        <main className= "vanguard" >
        <div className="vanguard-art" aria - hidden="true" />
            <div className="vanguard-grain" aria - hidden="true" />

            {/* Accessible controls aligned with the desktop artwork */ }
                < nav className = "vanguard-nav" aria - label="Main navigation" >
                    <button
          type="button"
    className = "vanguard-nav-button"
    aria - label="Home"
    title = "Home"
    onClick = { closePanel }
        >
        <Home aria - hidden="true" />
            </button>
            < button
    type = "button"
    className = "vanguard-nav-button"
    aria - label="How VEILBENCH works"
    title = "How it works"
    onClick = {() => setPanel("process")
}
        >
    <Layers3 aria - hidden="true" />
        </button>
        < button
type = "button"
className = "vanguard-nav-button"
aria - label="Security information"
title = "Security"
onClick = {() => setPanel("security")}
        >
    <ShieldCheck aria - hidden="true" />
        </button>
        < button
type = "button"
className = "vanguard-nav-button"
aria - label="About VEILBENCH"
title = "About"
onClick = {() => setPanel("about")}
        >
    <Info aria - hidden="true" />
        </button>
        </nav>

{/* Real interactive START button */ }
<button
        type="button"
className = "vanguard-start"
onClick = { onStart }
aria - label="Start VEILBENCH — sign in or activate account"
    >
    <span className="vanguard-start-mobile" >
        START < ArrowRight aria - hidden="true" size = { 23} />
            </span>
            </button>

{/* Compact responsive presentation */ }
<div className="vanguard-mobile-content" >
    <div className="vanguard-mobile-kicker" >
        SECURE MULTIPARTY COMPUTATION
            </div>
            < h1 > VEILBENCH </h1>
            < p > PRIVATE INPUTS.COLLECTIVE INSIGHT.</p>
                < button
type = "button"
className = "vanguard-mobile-cta"
onClick = { onStart }
    >
    ENTER SYSTEM < ArrowRight size = { 22} />
        </button>
        </div>

        < span className = "vanguard-index" aria - hidden="true" >
            <span className="active" />
                <span />
                < span />
                </span>

{/* Information overlay */ }
{
    panel && (
        <div
          className="vanguard-overlay"
    onMouseDown = {(event) => {
        if (event.target === event.currentTarget) {
            closePanel();
        }
    }
}
        >
    <section
            className="vanguard-panel"
role = "dialog"
aria - modal="true"
aria - labelledby="vanguard-panel-title"
    >
    <div className="vanguard-panel-top" >
        <span>VEILBENCH // SYSTEM INFORMATION</span>
        < button
type = "button"
onClick = { closePanel }
aria - label="Close information panel"
    >
    <X size={ 23 } />
        </button>
        </div>

{
    panel === "process" && (
        <>
        <span className="vanguard-panel-number" >01 / PROTOCOL </span>
            < h2 id = "vanguard-panel-title" > HOW IT WORKS </h2>
                <p>
                  Three founders contribute private salary inputs.
                  Each founder submits directly to an assigned MPC
    party.Once all submissions are ready, the
                  administrator starts the secure computation.
                </p>
        < div className = "vanguard-panel-steps" >
            <span>01 — CREATE SESSION </span>
                < span >02 — SUBMIT PRIVATELY </span>
                    < span >03 — COMPUTE AGGREGATE </span>
                        </div>
                        </>
            )
}

{
    panel === "security" && (
        <>
        <span className="vanguard-panel-number" >02 / PRIVACY </span>
            < h2 id = "vanguard-panel-title" > BUILT FOR PRIVACY </h2>
                <p>
                  VEILBENCH uses secure multiparty computation
                  to calculate a combined salary total and average.
                  Individual salary values are not displayed in
        the administrator's results.
            </p>
            <p>
                  This demonstration uses shared hosting
    infrastructure.It does not provide independent
                  organizational control of each MPC party.
                </p>
        </>
            )
}

{
    panel === "about" && (
        <>
        <span className="vanguard-panel-number" >03 / PROJECT </span>
            < h2 id = "vanguard-panel-title" > VEILBENCH </h2>
                <p>
                  A privacy - preserving benchmarking demonstration
                  powered by secure multiparty computation.
                </p>
        <p>
                  Designed to show how multiple participants can
                  calculate collective statistics without publishing
                  their individual inputs.
                </p>
        </>
            )
}

<button
              type="button"
className = "vanguard-panel-enter"
onClick = { onStart }
    >
    ENTER VEILBENCH < ArrowRight size = { 21} />
        </button>
        </section>
        </div>
      )}
</main>
  );
}
