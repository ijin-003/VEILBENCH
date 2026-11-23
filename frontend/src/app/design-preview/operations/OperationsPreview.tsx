"use client";
import { useState } from "react";
import { ArrowRight, LockKeyhole } from "lucide-react";
import { OperationsFounderArtwork, OperationsReactor, OperationsResults } from "../../OperationsScreens";

/** Synthetic-only visual preview. No credentials, sessions, backend calls or salaries persisted. */
export default function OperationsPreview() {
  const [view,setView]=useState<"reactor"|"founder"|"result">("reactor");
  const [count,setCount]=useState(0);
  const [computing,setComputing]=useState(false);
  const [sealed,setSealed]=useState(false);
  const [armed,setArmed]=useState(false);
  function simulateComputation() {
    if (count!==3 || computing)return;
    setComputing(true);
    window.setTimeout(()=>{setComputing(false);setView("result");},1400);
  }
  return <div className="vb-ops-preview">
    <div className="vb-ops-preview-top"><b>VEILBENCH / VISUAL DESIGN REVIEW</b><span>DEMO STATES ONLY — NO BACKEND CONNECTION</span><nav aria-label="Preview sections">
      <button onClick={()=>setView("reactor")} type="button" aria-current={view==="reactor"?"page":undefined}>01 / REACTOR</button>
      <button onClick={()=>setView("founder")} type="button" aria-current={view==="founder"?"page":undefined}>02 / FOUNDER</button>
      <button onClick={()=>setView("result")} type="button" aria-current={view==="result"?"page":undefined}>03 / RESULTS</button>
    </nav></div>
    <div className="vb-ops">
      {view==="reactor" && <OperationsReactor submitted={new Set(Array.from({length:count},(_,i)=>i))} state={computing?"computing":count===3?"ready":"created"} connected connecting={false}
        headline={computing?"SECURE COMPUTATION IN PROGRESS":count===3?"ALL CARTRIDGES DOCKED":`${count} OF 3 INPUTS SECURED`}
        busy={computing} computing={computing} hasSession canCompute={count===3&&!computing} complete={false}
        onTools={()=>setCount(0)} onCreate={()=>setCount(0)} onRefresh={()=>setCount(n=>Math.min(3,n+1))} onCompute={simulateComputation} onReveal={()=>setView("result")}/>}
      {view==="founder" && <section id="panel-founder" className={`panel active founder-panel ${armed?"is-armed":""} ${sealed?"is-sealed sealed":""}`} aria-label="Synthetic founder screen">
        <OperationsFounderArtwork partyId="0" sealed={sealed} armed={armed} sending={false}/>
        <div className="founder-right"><div className="panel-eyebrow">PRIVATE CHANNEL / FOUNDER 01</div><h1 className="impact"><span>SUBMIT</span><span>YOUR SALARY.</span></h1><p className="panel-eyebrow">YOUR VALUE REMAINS PRIVATE.</p>
          {sealed?<p className="founder-submission-confirmed" role="status">INPUT SEALED / VISUAL DEMO ONLY</p>:<div className="founder-form"><label className="founder-label" htmlFor="preview-amount">SYNTHETIC VALUE / DEMO ONLY</label><div className="salary-shell"><input id="preview-amount" type="text" inputMode="numeric" autoComplete="off" placeholder="Enter a synthetic amount" onChange={e=>setArmed(Boolean(e.target.value))}/></div>
            <button type="button" className="primary" disabled={!armed} onClick={()=>setSealed(true)}><LockKeyhole size={23}/> SEAL &amp; SUBMIT <ArrowRight size={22}/></button><p className="founder-privacy">Visual illustration only. No backend communication or data storage.</p></div>}
        </div>
      </section>}
      {view==="result" && <OperationsResults sum={180000} average={60000} onBack={()=>setView("reactor")}/>}
    </div>
    <div className="vb-ops-preview-bottom"><button onClick={()=>{setCount(n=>Math.min(3,n+1));setView("reactor");}} type="button">SIMULATE FOUNDER SUBMISSION</button><button onClick={()=>{setCount(0);setSealed(false);setArmed(false);setComputing(false);setView("reactor");}} type="button">RESET VISUAL DEMO</button></div>
    <style jsx>{`
      .vb-ops-preview-top,.vb-ops-preview-bottom{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;padding:12px 24px;background:#130b10;color:#fff5e9;font:900 11px Arial,sans-serif;letter-spacing:.08em}
      .vb-ops-preview-top nav,.vb-ops-preview-bottom{display:flex;gap:8px;flex-wrap:wrap}
      button{background:#ec0e30;color:#fff7ec;border:2px solid #fff4e6;padding:9px 14px;font-weight:900;cursor:pointer}
      button:hover,button[aria-current='page']{background:#fff4e6;color:#160c10}
      .vb-ops-preview-top span{color:#ffc4c8}
    `}</style>
  </div>;
}