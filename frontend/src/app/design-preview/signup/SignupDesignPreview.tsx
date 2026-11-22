"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import AuthGateway from "../../AuthGateway";

/** Safe, visual-only account activation. Never calls backend APIs. */
export default function SignupDesignPreview() {
  const [activate, setActivate] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [invitation, setInvitation] = useState("");
  const [message, setMessage] = useState("VISUAL PREVIEW ONLY — DO NOT ENTER REAL CREDENTIALS.");
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPassword("");
    setInvitation("");
    setMessage("Design preview only. No account was created and no request was sent.");
  }
  return (
    <>
      <AuthGateway
        activate={activate}
        busy={false}
        message={message}
        username={username}
        password={password}
        invitation={invitation}
        onUsernameChange={setUsername}
        onPasswordChange={setPassword}
        onInvitationChange={setInvitation}
        onSubmit={submit}
        onToggleActivate={() => {setActivate(value => !value);setPassword("");setInvitation("");setMessage("VISUAL PREVIEW ONLY — DO NOT ENTER REAL CREDENTIALS.");}}
        onBack={() => {window.location.assign("/design-preview");}}
      />
      <span className="vb-board-demo-marker" aria-label="Preview environment only">DESIGN PREVIEW · NO BACKEND REQUESTS</span>
    </>
  );
}
