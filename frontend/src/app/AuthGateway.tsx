"use client";

import { useRef, useState } from "react";
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

const COMMON_PASSWORDS = new Set([
  "passwordpassword", "password123456", "123456789012",
  "qwerty123456", "letmein123456", "adminadminadmin",
]);

function checkPasswordQuality(value: string, username: string) {
  const lower = value.toLowerCase();
  const tooCommon = COMMON_PASSWORDS.has(lower) || (value.length > 0 && new Set(value).size === 1) ||
    (username.length >= 3 && lower.includes(username.toLowerCase()));
  const lengthOk = value.length >= 12 && value.length <= 128;
  const groups = [/[a-z]/i, /\d/, /[^a-z0-9\s]/i, /\s/].filter((pattern) => pattern.test(value)).length;
  const score = !lengthOk ? 0 : tooCommon ? 1 :
    Math.min(4, 1 + Number(value.length >= 16) + Number(value.length >= 20) + Number(groups >= 2));
  const label = ["TOO SHORT", "WEAK", "FAIR", "GOOD", "STRONG"][score];
  return { score, label, lengthOk, tooCommon };
}

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
  const [confirmPassword, setConfirmPassword] = useState("");
  const quality = checkPasswordQuality(password, username);
  const passwordsMatch = Boolean(confirmPassword) && password === confirmPassword;
  const validUsername = /^[a-z0-9][a-z0-9_.-]{2,79}$/.test(username);
  const validInvitation = /^[A-Za-z0-9_-]{20,128}$/.test(invitation);
  const canActivate = validUsername && validInvitation && quality.lengthOk && !quality.tooCommon && passwordsMatch;
  const graphicRef = useRef<HTMLDivElement>(null);

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
            <strong>{activate ? "INITIALIZE." : "VERIFIED."}</strong>
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
            <span className="vb-auth-heading-shadow" aria-hidden="true">{activate ? "ACTIVATE" : "ENTER"}</span>
            <h1>{activate ? "ACTIVATE" : "ENTER"}<em>{activate ? "ACCOUNT." : "SYSTEM."}</em></h1>
          </div>
          <p className="vb-auth-intro">{activate ? "Accept your invitation. Establish your access." : "Your credentials. Your secure workspace."}</p>

          <form className="vb-auth-form" onSubmit={(event) => { if (activate && !canActivate) { event.preventDefault(); return; } void onSubmit(event); }}>
            <label className="vb-auth-field">
              <span>01 / USERNAME</span>
              <input required name="username" autoComplete="username" pattern="[a-z0-9][a-z0-9_.-]+" minLength={3} maxLength={80} value={username} onChange={(e) => onUsernameChange(e.target.value.toLowerCase())} placeholder="your.username" />
            </label>
            {activate && (
              <label className="vb-auth-field">
                <span>02 / INVITATION CODE</span>
                <input required name="invitation" type="password" autoComplete="off" minLength={20} maxLength={128} value={invitation} onChange={(e) => onInvitationChange(e.target.value)} placeholder="Enter your invitation code" />
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
            {activate && (
              <div className="vb-auth-password-check">
                <div className="vb-auth-strength-head"><span>LIVE PASSWORD STRENGTH</span><strong>{quality.label}</strong></div>
                <div className="vb-auth-strength-bars" role="meter" aria-label="Password strength" aria-valuemin={0} aria-valuemax={4} aria-valuenow={quality.score}>
                  {[0, 1, 2, 3].map((index) => <i key={index} className={quality.score > index ? "active" : ""} />)}
                </div>
                <p aria-live="polite">
                  {!quality.lengthOk ? "Use 12–128 characters; longer passphrases are stronger." :
                    quality.tooCommon ? "Avoid common patterns or including your username." :
                    "Length matters most. A unique passphrase is recommended."}
                </p>
              </div>
            )}
            {activate && (
              <label className="vb-auth-field">
                <span>04 / CONFIRM PASSWORD</span>
                <span className="vb-auth-input-wrap">
                  <input required name="confirm_password" type={showPassword ? "text" : "password"} autoComplete="new-password" value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Enter the same password again" minLength={12} maxLength={128} />
                </span>
                {confirmPassword && <span className={passwordsMatch ? "vb-auth-match is-match" : "vb-auth-match"} role="status" aria-live="polite">
                  {passwordsMatch ? "PASSWORDS MATCH" : "PASSWORDS DO NOT MATCH"}
                </span>}
              </label>
            )}
            {message && <p className="vb-auth-message" role="status" aria-live="polite">{message}</p>}
            <button className="vb-auth-submit" disabled={busy || !validUsername || !quality.lengthOk || (activate && !canActivate)} type="submit">
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
