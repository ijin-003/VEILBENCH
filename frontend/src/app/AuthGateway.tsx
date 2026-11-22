"use client";

import { useEffect, useRef, useState } from "react";
import type { CSSProperties, FormEvent, PointerEvent } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Eye,
  EyeOff,
  LockKeyhole,
  ShieldCheck,
} from "lucide-react";
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

export default function AuthGateway({
  activate,
  busy,
  message,
  username,
  password,
  invitation,
  onUsernameChange,
  onPasswordChange,
  onInvitationChange,
  onSubmit,
  onToggleActivate,
  onBack,
}: AuthGatewayProps) {
  const [showPassword, setShowPassword] = useState(false);
  const graphicRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setShowPassword(false);
  }, [activate]);

  function moveGraphic(event: PointerEvent<HTMLElement>) {
    if (event.pointerType !== "mouse" || !graphicRef.current) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width - 0.5;
    const y = (event.clientY - rect.top) / rect.height - 0.5;
    graphicRef.current.style.setProperty("--auth-x", `${x * 24}px`);
    graphicRef.current.style.setProperty("--auth-y", `${y * 18}px`);
    graphicRef.current.style.setProperty("--auth-cursor-x", `${(x + .5) * 100}%`);
    graphicRef.current.style.setProperty("--auth-cursor-y", `${(y + .5) * 100}%`);
  }

  function resetGraphic() {
    graphicRef.current?.style.setProperty("--auth-x", "0px");
    graphicRef.current?.style.setProperty("--auth-y", "0px");
  }

  return (
    <main className="vb-auth vb-auth-v2" data-mode={activate ? "activate" : "login"}>
      <section
        className="vb-auth-motion"
        onPointerMove={moveGraphic}
        onPointerLeave={resetGraphic}
        aria-label="Animated VEILBENCH access illustration"
      >
        <div className="vb-auth-motion-inner" ref={graphicRef} style={{"--auth-x":"0px","--auth-y":"0px"} as CSSProperties}>
          <div className="vb-auth-motion-glow" aria-hidden="true" />
          <div className="vb-auth-giant-index" aria-hidden="true">{activate ? "02" : "01"}</div>
          <div className="vb-auth-cross" aria-hidden="true">+</div>
          <div className="vb-auth-vector" aria-hidden="true">
            <div className="vb-auth-vector-ring ring-one" />
            <div className="vb-auth-vector-ring ring-two" />
            <div className="vb-auth-vector-ring ring-three" />
            <div className="vb-auth-emblem">
              <svg viewBox="0 0 160 160" fill="none" role="presentation" focusable="false">
                <path d="M80 14 133 37v37c0 39-22 60-53 75C49 134 27 113 27 74V37L80 14Z" stroke="currentColor" strokeWidth="6" strokeLinejoin="round"/>
                <path d="M52 78 73 99l37-40" stroke="currentColor" strokeWidth="9" strokeLinecap="square" strokeLinejoin="round"/>
                <path d="M80 0v19M80 143v17M0 80h24M136 80h24" stroke="currentColor" strokeWidth="3"/>
              </svg>
            </div>
          </div>
          <div className="vb-auth-slice slice-a" aria-hidden="true" />
          <div className="vb-auth-slice slice-b" aria-hidden="true" />
          <div className="vb-auth-slice slice-c" aria-hidden="true" />
          <div className="vb-auth-art-caption" aria-hidden="true">
            <span>IDENTITY //</span>
            <strong>{activate ? "INITIALIZE." : "PRIVATE ACCESS."}</strong>
          </div>
          <span className="vb-auth-motion-tag" aria-hidden="true">VEILBENCH / ACCESS PROTOCOL</span>
          <span className="vb-auth-motion-bottom" aria-hidden="true">NO INDIVIDUAL INPUTS ON DISPLAY</span>
        </div>
      </section>

      <section className="vb-auth-side" aria-label={activate ? "Account activation" : "Sign in"}>
        <header className="vb-auth-header">
          <button className="vb-auth-back" type="button" onClick={onBack} aria-label="Return to homepage">
            <ArrowLeft size={17} aria-hidden="true" /> BACK
          </button>
          <span className="vb-auth-wordmark">VEILBENCH <b>//</b></span>
        </header>

        <div className="vb-auth-content">
          <div className="vb-auth-kicker"><span className="vb-auth-pulse" /> AUTHENTICATION / {activate ? "02" : "01"}</div>
          <div className="vb-auth-heading-wrap">
            <span className="vb-auth-heading-shadow" aria-hidden="true">{activate ? "ACTIVATE" : "ACCESS"}</span>
            <h1>{activate ? "ACTIVATE" : "ACCESS"}<em>{activate ? "ACCOUNT." : "GATEWAY."}</em></h1>
          </div>
          <p className="vb-auth-intro">{activate ? "Accept your private invitation to continue." : "AUTHENTICATED ACCESS ONLY."}</p>

          <form className="vb-auth-form" onSubmit={onSubmit}>
            <label className="vb-auth-field">
              <span>01 / USERNAME</span>
              <input required name="username" autoComplete="username" pattern="[a-z0-9][a-z0-9_.-]+" minLength={3} maxLength={80} value={username} onChange={(e) => onUsernameChange(e.target.value.toLowerCase())} placeholder="your.username" />
            </label>
            {activate && (
              <label className="vb-auth-field">
                <span>02 / INVITATION CODE</span>
                <input required name="invitation" type="password" autoComplete="off" value={invitation} onChange={(e) => onInvitationChange(e.target.value)} placeholder="Enter your invitation code" />
              </label>
            )}
            <label className="vb-auth-field">
              <span>{activate ? "03" : "02"} / {activate ? "NEW PASSWORD (12–128 CHARACTERS)" : "PASSWORD"}</span>
              <span className="vb-auth-input-wrap">
                <input required name="password" type={showPassword ? "text" : "password"} minLength={12} maxLength={128} autoComplete={activate ? "new-password" : "current-password"} value={password} onChange={(e) => onPasswordChange(e.target.value)} placeholder={activate ? "Create a secure password" : "Enter your password"} />
                <button type="button" className="vb-auth-reveal" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword}>
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </span>
            </label>
            {message && <p className="vb-auth-message" role="status" aria-live="polite">{message}</p>}
            <button className="vb-auth-submit" disabled={busy} type="submit">
              <span>{busy ? "PROCESSING…" : activate ? "ACTIVATE ACCOUNT" : "ACCESS VEILBENCH"}</span>
              {busy ? <span className="vb-auth-spinner" aria-hidden="true" /> : <ArrowRight size={22} aria-hidden="true" />}
            </button>
          </form>

          <div className="vb-auth-footactions">
            <button type="button" disabled={busy} onClick={onToggleActivate} className="vb-auth-switch">
              {activate ? "ALREADY ACTIVATED? SIGN IN" : "HAVE AN INVITATION? ACTIVATE"}
              <ArrowRight size={15} aria-hidden="true" />
            </button>
            <GuidedTour role="welcome" />
          </div>
          <p className="vb-auth-disclaimer"><ShieldCheck size={14} aria-hidden="true" /> Shared infrastructure demo; parties are not independently hosted.</p>
        </div>

        <footer className="vb-auth-footer"><span><LockKeyhole size={13} /> SECURE ACCESS</span><span>RED VANGUARD / 02</span></footer>
      </section>
    </main>
  );
}
