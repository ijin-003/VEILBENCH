"use client";

import { useRef, useState } from "react";
import type { FormEvent, PointerEvent } from "react";
import { ArrowLeft, ArrowRight, Eye, EyeOff, LockKeyhole } from "lucide-react";
import { GuidedTour } from "./LearningCenter";
import "./approved-board.css";

type AuthGatewayProps = {
  activate: boolean;
  busy: boolean;
  message: string;
  username: string;
  password: string;
  invitation: string;
  onUsernameChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onInvitationChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void | Promise<void>;
  onToggleActivate: () => void;
  onBack: () => void;
};

/** Purely decorative editorial illustration. Contains no personal or credential data. */
export function AccessPadlockArtwork() {
  return (
    <svg className="vb-board-padlock" viewBox="0 0 720 650" role="img" aria-label="Large chained padlock against red and black graphic shapes" preserveAspectRatio="xMidYMid slice">
      <defs>
        <pattern id="vb-board-grain" width="9" height="9" patternUnits="userSpaceOnUse">
          <circle cx="2" cy="2" r=".6" fill="#151313" opacity=".13" />
        </pattern>
      </defs>
      <rect width="720" height="650" fill="#e30d20"/>
      <path d="M-35 0H215L-60 510Z" fill="#151313"/>
      <path d="M110 0H340L-15 650H-150Z" fill="#101010"/>
      <path d="M390 -20H720V180L510 490 370 650 150 650Z" fill="#f2162b"/>
      <path d="M555 -20H720V650H635L390 650Z" fill="#cc0b20" opacity=".45"/>
      <path d="M0 470L265 650H-25Z" fill="#151313"/>
      <path d="M445 650L720 530V650Z" fill="#151313"/>
      <path d="M-20 250L198 380 155 430-20 320Z" fill="#ffefe2" opacity=".95"/>
      {/* Decorative chains: individual outlined links crossing the left and upper corners. */}
      <g className="vb-board-chain vb-board-chain--top" transform="translate(-100 125) rotate(-28 200 0)" stroke="#fff5ea" strokeWidth="13" fill="#151313">
        {Array.from({length:8},(_,i)=><rect key={i} x={i*83} y={0} width="104" height="52" rx="25" transform={`rotate(${i%2===0?10:-10} ${i*83+52} 26)`} />)}
      </g>
      <g className="vb-board-chain vb-board-chain--bottom" transform="translate(-128 516) rotate(-31 200 0)" stroke="#151313" strokeWidth="14" fill="#f8eee0">
        {Array.from({length:8},(_,i)=><rect key={i} x={i*86} y="0" width="104" height="48" rx="24" />)}
      </g>
      {/* Padlock shadow, shackle and body: near the proportions of the approved reference. */}
      <g className="vb-board-lock-body" transform="translate(118 100) rotate(-10 205 260)">
        <path d="M128 250V174C128 65 193 16 278 16S428 65 428 174V258H346V174C346 122 319 95 278 95S210 122 210 174V250Z" fill="#141313" stroke="#fff5e8" strokeWidth="12" />
        <path d="M166 248V174C166 89 213 55 278 55S390 89 390 174V248" stroke="#e30d20" strokeWidth="16" fill="none"/>
        <path d="M73 264L400 209 433 459 120 509Z" fill="#151313" stroke="#fff5e8" strokeWidth="13"/>
        <path d="M90 267L401 216 430 450 121 502Z" fill="#ed0d24" stroke="#171314" strokeWidth="8"/>
        <path d="M88 267L297 234 122 498Z" fill="#fff7e8"/>
        <path d="M278 317C251 317 237 335 237 357C237 372 245 384 256 391L243 445H306L293 392C305 384 312 371 312 357C312 334 299 317 278 317Z" fill="#151313"/>
        <path d="M105 480L436 425" stroke="#151313" strokeWidth="12"/>
      </g>
      <path d="M-40 612L680 434" stroke="#151313" strokeWidth="16"/>
      <circle className="vb-board-target-ring" cx="317" cy="276" r="172" fill="none" stroke="#fdf3e6" strokeWidth="1.5" opacity=".55"/>
      <path d="M318 90V125M318 434V466M133 276H164M477 276H506" stroke="#fff8ee" strokeWidth="2" opacity=".8"/>
      <rect width="720" height="650" fill="url(#vb-board-grain)" pointerEvents="none"/>
    </svg>
  );
}

export default function AuthGateway({
  activate, busy, message, username, password, invitation,
  onUsernameChange, onPasswordChange, onInvitationChange,
  onSubmit, onToggleActivate, onBack,
}: AuthGatewayProps) {

  const [showPassword, setShowPassword] = useState(false);
  const artRef = useRef<HTMLElement>(null);

  // CSS-variable parallax avoids React renders on each pointer event.
  // Motion is disabled for touch and prefers-reduced-motion.
  function animateArtwork(event: PointerEvent<HTMLElement>) {
    if (event.pointerType !== "mouse" || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const node = artRef.current;
    if (!node) return;
    const rect = node.getBoundingClientRect();
    const horizontal = Math.max(-.5, Math.min(.5, (event.clientX - rect.left) / rect.width - .5));
    const vertical = Math.max(-.5, Math.min(.5, (event.clientY - rect.top) / rect.height - .5));
    node.style.setProperty("--vb-art-x", (horizontal * 19).toFixed(1) + "px");
    node.style.setProperty("--vb-art-y", (vertical * 17).toFixed(1) + "px");
    node.style.setProperty("--vb-lock-x", (horizontal * -21).toFixed(1) + "px");
    node.style.setProperty("--vb-lock-y", (vertical * -14).toFixed(1) + "px");
    node.style.setProperty("--vb-chain-x", (horizontal * 12).toFixed(1) + "px");
    node.style.setProperty("--vb-cursor-x", ((horizontal + .5) * 100).toFixed(1) + "%");
    node.style.setProperty("--vb-cursor-y", ((vertical + .5) * 100).toFixed(1) + "%");
  }

  function resetArtwork() {
    const node = artRef.current;
    if (!node) return;
    for (const property of ["--vb-art-x", "--vb-art-y", "--vb-lock-x", "--vb-lock-y", "--vb-chain-x"]) {
      node.style.setProperty(property, "0px");
    }
  }
  return (
    <main className="vb-board-access" data-mode={activate ? "activate" : "login"}>
      <section ref={artRef} onPointerMove={animateArtwork} onPointerLeave={resetArtwork} className="vb-board-access-art" aria-label="Animated chained padlock illustration">
        <AccessPadlockArtwork />
        <div className="vb-board-cursor-glow" aria-hidden="true" />
        <div className="vb-board-speed-slash" aria-hidden="true" />
        <div className="vb-board-motion-reticle" aria-hidden="true"><i /><i /></div>
        <div className="vb-board-art-logo" aria-hidden="true">VEILBENCH <b>/</b></div>
        <span className="vb-board-art-edge" aria-hidden="true">ACCESS / CONTROLLED</span>
      </section>
      <section className="vb-board-access-panel" aria-label={activate ? "Account activation" : "Sign in"}>
        <header className="vb-board-access-header">
          <button type="button" onClick={onBack} className="vb-board-access-back"><ArrowLeft size={17} /> BACK</button>
          <span className="vb-board-access-brand">VEILBENCH <b>//</b></span>
        </header>
        <div className="vb-board-access-main">
          <span className="vb-board-access-index"><i /> {activate ? "02 / INVITATION ACCESS" : "01 / AUTHENTICATED ACCESS"}</span>
          <h1 className="vb-board-access-title"><>ACCESS<br/>GATEWAY</></h1>
          <p className="vb-board-access-intro">{activate ? "INVITATION-ONLY ACCOUNT ACTIVATION" : "AUTHENTICATED ACCESS ONLY"}</p>
          <form className="vb-board-access-form" onSubmit={onSubmit}>
            <label>
              <span>USERNAME</span>
              <input required name="username" autoComplete="username" pattern="[a-z0-9][a-z0-9_.-]+" minLength={3} maxLength={80} value={username} onChange={e=>onUsernameChange(e.target.value.toLowerCase())} placeholder="Username"/>
            </label>
            {activate && <label>
              <span>INVITATION CODE</span>
              <input required name="invitation" type="password" autoComplete="off" value={invitation} onChange={e=>onInvitationChange(e.target.value)} placeholder="Invitation code"/>
            </label>}
            <label>
              <span>{activate ? "NEW PASSWORD (12–128 CHARACTERS)" : "PASSWORD"}</span>
              <span className="vb-board-access-password">
                <input required name="password" type={showPassword?"text":"password"} minLength={12} maxLength={128} autoComplete={activate?"new-password":"current-password"} value={password} onChange={e=>onPasswordChange(e.target.value)} placeholder="Password"/>
                <button type="button" onClick={()=>setShowPassword(v=>!v)} aria-label={showPassword?"Hide password":"Show password"} aria-pressed={showPassword}>{showPassword?<EyeOff size={18}/>:<Eye size={18}/>}</button>
              </span>
            </label>
            {message && <p className="vb-board-access-message" role="status" aria-live="polite">{message}</p>}
            <button className="vb-board-access-submit vb-board-magnetic" type="submit" disabled={busy}>
              <span>{busy?"PROCESSING…":activate?"ACTIVATE ACCOUNT":"SIGN IN"}</span><ArrowRight size={26}/>
            </button>
          </form>
          <div className="vb-board-access-extras">
            <button type="button" disabled={busy} onClick={()=>{setShowPassword(false);onToggleActivate();}}>
              {activate?"ALREADY ACTIVATED? SIGN IN":"HAVE AN INVITATION? ACTIVATE"} <ArrowRight size={15}/>
            </button>
            <GuidedTour role="welcome"/>
          </div>
          <p className="vb-board-access-caveat"><LockKeyhole size={14}/> Shared-host academic demonstration; use synthetic data only.</p>
        </div>
        <footer className="vb-board-access-footer"><span>VEILBENCH / PRIVATE ACCESS</span><span>RED VANGUARD / 02</span></footer>
      </section>
    </main>
  );
}
