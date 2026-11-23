"use client";

import { useRef } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import Image from "next/image";
import { ArrowRight, LockKeyhole, Plus, RefreshCw } from "lucide-react";
import "./internal-red-black.css";

const FOUNDERS = [0, 1, 2] as const;
const fmt = new Intl.NumberFormat("en-PK", {maximumFractionDigits:2});

type ReactorProps = {
  submitted: ReadonlySet<number>;
  state: string;
  connected: boolean;
  connecting: boolean;
  headline: string;
  busy: boolean;
  computing: boolean;
  hasSession: boolean;
  canCompute: boolean;
  complete: boolean;
  onTools: () => void;
  onCreate: () => void;
  onRefresh: () => void;
  onCompute: () => void;
  onReveal: () => void;
};

/** Presentation art contains no individual salaries and reads only public status metadata. */
export function OperationsReactor({submitted,state,connected,connecting,headline,busy,computing,hasSession,canCompute,complete,onTools,onCreate,onRefresh,onCompute,onReveal}:ReactorProps) {
  const artRef = useRef<HTMLDivElement>(null);
  const count = FOUNDERS.filter(id => submitted.has(id)).length;
  function pointerMove(event:ReactPointerEvent<HTMLDivElement>) {
    if(event.pointerType!=="mouse" || window.matchMedia("(prefers-reduced-motion: reduce)").matches)return;
    const art=artRef.current;if(!art)return;
    const b=art.getBoundingClientRect();
    art.style.setProperty("--mouse-x",`${((event.clientX-b.left)/b.width-.5)*20}px`);
    art.style.setProperty("--mouse-y",`${((event.clientY-b.top)/b.height-.5)*12}px`);
  }
  function resetPointer(){artRef.current?.style.setProperty("--mouse-x","0px");artRef.current?.style.setProperty("--mouse-y","0px");}
  return <section id="panel-admin" className={`panel active ops-reactor ${computing?"ops-computing":""} ${state==="ready"?"ops-ready":""}`} aria-label="Administrator MPC reactor">
    <div className="speedlines" aria-hidden="true"/><div className="diagonal top" aria-hidden="true"/><div className="cross one" aria-hidden="true"/><div className="cross two" aria-hidden="true"/>
    <div className="admin-title"><div className="panel-eyebrow">THREE-FOUNDER SECURE COMPUTATION</div><h1 className="impact"><span>MPC</span><span>REACTOR.</span></h1><div className="title-rule"/><div className="side-note">THREE PRIVATE CHANNELS<br/>ONE RECONSTRUCTED AGGREGATE</div></div>
    <button className="tool-toggle" type="button" onClick={onTools}>☷ &nbsp; SESSION TOOLS</button>
    <div className="reactor-stage" ref={artRef} onPointerMove={pointerMove} onPointerLeave={resetPointer} aria-label={`${count} of 3 founder inputs received`}>
      <div className="reactor-aura" aria-hidden="true"/><div className="reactor-floor" aria-hidden="true"/>
      <Image className="reactor-machine" src="/images/reactor-monolith-v7.png" alt="" width={1086} height={1448} priority sizes="(max-width:760px) 70vw,55vw" />
      <div className="pod-connections" aria-hidden="true"><svg viewBox="0 0 1000 500" preserveAspectRatio="none"><path d="M500,62 C500,160 145,88 145,317 M500,90 L500,310 M500,60 C500,160 851,88 851,318"/><path className="highlight" d="M500,62 C500,160 145,88 145,317 M500,90 L500,310 M500,60 C500,160 851,88 851,318"/></svg></div>
      <div className="pod-row" role="list" aria-label="Founder submission status">
        {FOUNDERS.map((id)=><div key={id} role="listitem" className={`pod ${submitted.has(id)?"received secured":""} ${computing?"computing processing":""}`} data-party={id} aria-label={`Founder ${id+1}: ${submitted.has(id)?"submitted":"waiting"}`}>
          <strong>FOUNDER 0{id+1}</strong><small><i className="dot"/><span>{submitted.has(id)?"SUBMITTED":"WAITING"}</span></small><i className="pod-leg" aria-hidden="true"/>
        </div>)}
      </div>
    </div>
    <div className="reactor-bottom">
      <div className="mini-state" role="status" aria-live="polite"><span>LIVE SESSION / <b>{String(count).padStart(2,"0")}</b> OF 03</span><strong>{headline}</strong></div>
      <div className="reactor-controls">
        {hasSession && <button type="button" className="secondary" disabled={busy} onClick={onRefresh}><RefreshCw size={16}/> REFRESH</button>}
        {!hasSession ? <button type="button" className="primary" disabled={busy} onClick={onCreate}><Plus size={21}/> CREATE SESSION <ArrowRight/></button>
        : complete ? <button type="button" className="primary" onClick={onReveal}>REVEAL RESULT <ArrowRight/></button>
        : <button type="button" className="primary" disabled={!canCompute} onClick={onCompute}><span aria-hidden="true">⚙</span> {computing?"COMPUTING…":"COMPUTE"} <ArrowRight/></button>}
      </div>
    </div>
    <div className="hud-corner"><b>///</b> THREE LOGICAL PARTIES / ONE SHARED HOST</div>
    <div className="ops-link-state" role="status">● {connecting?"CONNECTING":connected?"COORDINATOR ONLINE":"LINK UNVERIFIED"}</div>
  </section>;
}

export function OperationsResults({sum,average,onBack}: {sum:number;average:number;onBack:()=>void}) {
  return <section id="panel-result" className="panel active result-panel" aria-label="Verified MPC aggregate results" aria-live="polite">
    <div className="result-ribbon" aria-hidden="true"/>
    <div className="result-art" aria-hidden="true"><Image className="character" src="/images/veilbench-character-light.png" alt="" width={1672} height={941} sizes="(max-width:760px) 70vw,52vw" /></div>
    <div className="result-portraits" aria-hidden="true">{FOUNDERS.map(id=><div className="portrait" key={id}><svg viewBox="0 0 280 120"><path d="M60 110 35 84 40 49 25 31 54 27 64 12 78 24 90 3 112 22 136 12 140 29 159 38 146 54 168 69 150 79 144 100 119 100 100 111Z" fill="#fff8eb"/></svg></div>)}</div>
    <div className="ribbon-line" aria-hidden="true"/><div className="ribbon-line line2" aria-hidden="true"/><div className="ribbon-line line3" aria-hidden="true"/>
    <div className="result-right"><h1 className="impact"><span>COMPUTATION</span><span>COMPLETE.</span></h1><div className="panel-eyebrow">VERIFIED AGGREGATE RESULTS</div>
      <div className="result-block"><label>TOTAL (SUM)</label><strong>{fmt.format(sum)}</strong></div>
      <div className="result-block"><label>AVERAGE</label><strong>{fmt.format(average)}</strong></div>
      <div className="result-actions"><button type="button" className="secondary" onClick={onBack}>← BACK TO REACTOR</button></div>
    </div>
    <div className="result-side-mark">ONLY VERIFIED AGGREGATES DISPLAYED / 03</div>
  </section>;
}

export function OperationsFounderArtwork({partyId,sending,sealed,armed}: {partyId:string;sending:boolean;sealed:boolean;armed:boolean}) {
  return <>
    <div className="founder-left" aria-hidden="true"/><div className="cross one" aria-hidden="true"/>
    <div className="chamber" aria-hidden="true"><div className="glass-inner"><div className="glass-arc"/><div className="silhouette"/></div><div className="glass-head"/><div className="glass-foot"/><div className="seal-ribbon"><span className="seal-icon"><LockKeyhole size={30}/></span><span>{sealed?<>INPUT<br/>SEALED</>:sending?<>SECURE<br/>TRANSFER</>:<>PRIVATE INPUT<br/>SEAL</>}</span></div></div>
    <div className="founder-float-label">FOUNDER 0{Number(partyId)+1} / CONFIDENTIAL / SINGLE USE</div>
    <div className="confetti" aria-hidden="true"/><div className="confetti" aria-hidden="true"/>
    <span className="founder-live-state" aria-live="polite">{sealed?"RECEIPT VERIFIED":sending?"TRANSMITTING TO PARTY":armed?"READY TO SEAL":"PRIVATE CHANNEL"}</span>
  </>;
}