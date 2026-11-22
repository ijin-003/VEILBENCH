"use client";

import "./approved-board.css";

/** Real submission metadata only — never reads or receives private salary values. */
type Props = { submitted: ReadonlySet<number>; stage: string };
const FOUNDERS = [0, 1, 2] as const;

/**
 * Poster-style MPC machine built as crisp SVG, not a static screenshot.
 * Capsules derive their status exclusively from backend-confirmed party IDs.
 */
export default function ReactorStage({ submitted, stage }: Props) {
  const count = FOUNDERS.filter(id => submitted.has(id)).length;
  const running = stage === "computing";
  const completed = stage === "completed";
  const unitCenters = [207, 600, 993];
  return (
    <div className={`vb-ref-reactor ${running ? "vb-ref-reactor--computing" : ""} ${completed ? "vb-ref-reactor--completed" : ""}`}
      role="group" aria-label="MPC reactor showing three founder submission statuses">
      <svg viewBox="0 0 1200 590" className="vb-ref-machine" role="img" aria-labelledby="vb-reactor-title vb-reactor-desc">
        <title id="vb-reactor-title">Three-founder MPC reactor</title>
        <desc id="vb-reactor-desc">{count} of 3 founder submissions received. {running ? "Secure computation in progress." : completed ? "Aggregate computed." : "Waiting for authenticated administrator action."}</desc>
        <defs>
          <linearGradient id="vb-steel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#fff9e9"/><stop offset=".23" stopColor="#b3a59d"/><stop offset=".53" stopColor="#f9eee2"/><stop offset="1" stopColor="#69514b"/></linearGradient>
          <linearGradient id="vb-red-metal" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#7f0713"/><stop offset=".3" stopColor="#f5182a"/><stop offset=".65" stopColor="#cc0b1d"/><stop offset="1" stopColor="#49070e"/></linearGradient>
          <pattern id="vb-machine-grid" width="64" height="64" patternUnits="userSpaceOnUse"><path d="M64 0H0V64" fill="none" stroke="#141111" strokeWidth="1" opacity=".12"/></pattern>
        </defs>
        {/* White editorial stage, angular cuts, subtle drafting marks */}
        <path d="M0 450 235 387 456 458 1200 395V590H0Z" fill="#e9e0d3"/>
        <path d="M0 537 380 443 758 517 1200 442" fill="none" stroke="#141111" strokeWidth="10"/>
        <path d="M16 570 580 495 1200 570" fill="none" stroke="#131313" strokeWidth="6"/>
        <path d="M0 414 268 343 212 444 0 482Z" fill="#e61227"/>
        <path d="M1200 76 1028 183 1200 132Z" fill="#e61227"/>
        <path d="M44 210h50m-25-25v50 M1123 169h52m-26-26v52" stroke="#171313" strokeWidth="2" opacity=".5"/>
        {/* Suspended upper superstructure */}
        <g fill="#141313" stroke="#141313" strokeWidth="12" strokeLinecap="round">
          <path d="M386 -14 427 45 488 73M803 -14 765 47 700 73" fill="none"/>
          <path d="M535 -15 541 90M658 -15 658 90" fill="none"/>
          <path d="M601 -15V86" fill="none"/>
        </g>
        <path d="M554 0H651V85H554Z" fill="url(#vb-red-metal)" stroke="#121010" strokeWidth="9"/>
        <path d="M598 0V85M563 48H646" stroke="#130d0d" strokeWidth="9"/>
        {/* Suspended red ring: the central defining element of the reference */}
        <g className="vb-ref-ring">
          <ellipse cx="600" cy="129" rx="345" ry="83" fill="#161111" stroke="#160d0e" strokeWidth="18"/>
          <ellipse cx="600" cy="105" rx="344" ry="79" fill="url(#vb-red-metal)" stroke="#160e0f" strokeWidth="16"/>
          <ellipse cx="600" cy="105" rx="277" ry="49" fill="#141011" stroke="#ff7b65" strokeWidth="8"/>
          <ellipse cx="600" cy="107" rx="231" ry="32" fill="#aa071b" stroke="#0e090a" strokeWidth="14"/>
          <ellipse cx="600" cy="102" rx="181" ry="23" fill="#311014" stroke="#ed2638" strokeWidth="6"/>
          <path d="M287 113q310 88 620 0" fill="none" stroke="#fff3de" opacity=".32" strokeWidth="4"/>
          {Array.from({length:11},(_,i)=>{const x=288+i*62;return <path key={i} d={`M${x} 83l11 -8`} stroke="#fff3e3" strokeWidth="5" opacity=".55"/>;})}
        </g>
        {/* Central powerhouse and upper black/red cylinders */}
        <g>
          <path d="M515 140H685L731 414H467Z" fill="#171111" stroke="#0e0808" strokeWidth="12"/>
          <path d="M547 148H649L671 415H527Z" fill="url(#vb-red-metal)" stroke="#111" strokeWidth="10"/>
          <path d="M580 153H618V408H580Z" fill="#fa2230" opacity=".8"/>
          <path d="M511 187H686M497 246H705M477 324H722" stroke="#0c0c0c" strokeWidth="15"/>
          <path d="M523 209H669M509 265H681" stroke="#fff1e1" strokeWidth="3" opacity=".45"/>
          <rect x="564" y="206" width="74" height="127" rx="7" fill="#240b0e" stroke="#ff5a4c" strokeWidth="7"/>
          <path d="M601 229 621 262 601 304 581 262Z" fill="#f52433"/>
          <path d="M513 337H686L733 447H467Z" fill="#1a1113" stroke="#120d0d" strokeWidth="12"/>
          <path d="M520 354H681L696 425H501Z" fill="#b2081b" stroke="#0d0809" strokeWidth="10"/>
        </g>
        {/* Thick cables connect all three distinct MPC parties. */}
        <g fill="none" stroke="#151111" strokeLinecap="round" strokeLinejoin="round">
          <path d="M544 166C454 207 309 185 206 315" strokeWidth="22"/>
          <path d="M660 169C743 217 887 193 991 317" strokeWidth="22"/>
          <path d="M598 187V317" strokeWidth="26"/>
          <path d="M446 238C346 244 279 260 245 309" strokeWidth="8"/>
          <path d="M740 238C845 242 912 268 952 311" strokeWidth="8"/>
        </g>
        {/* Three large front-mounted cream capsules, mechanically attached. */}
        {FOUNDERS.map((id) => {
          const cx=unitCenters[id]; const received=submitted.has(id);
          return (
            <g key={id} className={`vb-ref-pod ${received?"vb-ref-pod--received":""}`} role="group"
              aria-label={`Founder ${id+1}: ${received?"submitted":"awaiting input"}`}>
              <path d={`M${cx-93} 416V484H${cx+93}V416`} fill="#1b1012" stroke="#110d0d" strokeWidth="13"/>
              <path d={`M${cx-122} 478H${cx+122}L${cx+148} 526H${cx-148}Z`} fill="#141010" stroke="#0b0808" strokeWidth="10"/>
              <path d={`M${cx-80} 475H${cx+80}L${cx+93} 498H${cx-93}Z`} fill="#bb0c20" stroke="#0d0809" strokeWidth="9"/>
              <rect x={cx-162} y="302" width="324" height="151" rx="64" fill="#141011" stroke="#0d090a" strokeWidth="13"/>
              <rect x={cx-153} y="309" width="306" height="135" rx="61" fill="url(#vb-steel)" stroke="#e01627" strokeWidth="13"/>
              <rect x={cx-121} y="319" width="242" height="113" rx="41" fill="#fff8eb" stroke="#1a1313" strokeWidth="9"/>
              <path d={`M${cx-138} 338l28 -17M${cx+111} 339l28 -17M${cx-136} 407l25 20M${cx+110} 427l25 -18`} stroke="#a40c1b" strokeWidth="8"/>
              <rect x={cx-169} y="340" width="18" height="74" rx="4" fill="#d40d23" stroke="#111" strokeWidth="7"/>
              <rect x={cx+151} y="340" width="18" height="74" rx="4" fill="#d40d23" stroke="#111" strokeWidth="7"/>
              <text x={cx} y="363" fontFamily="Arial, sans-serif" fontSize="23" fontStyle="italic" fontWeight="900" textAnchor="middle" fill="#161111">FOUNDER 0{id+1}</text>
              <circle cx={cx-62} cy="390" r="11" fill={received?"#18b93d":"#98918b"} stroke="#151313" strokeWidth="3" className="vb-ref-led"/>
              <text x={cx+8} y="398" fontFamily="Arial, sans-serif" fontSize="19" fontStyle="italic" fontWeight="900" textAnchor="middle" fill="#161111">{received?"SUBMITTED":"WAITING"}</text>
              <path d={`M${cx-75} 428h150`} stroke="#181313" strokeWidth="3" opacity=".4"/>
            </g>
          );
        })}
        <path d="M0 548 290 528 598 559 890 528 1200 553" stroke="#f0ede4" strokeWidth="7" fill="none"/>
        <path d="M0 590V557L298 520 600 570 915 530 1200 558V590" fill="#171212"/>
        <rect width="1200" height="590" fill="url(#vb-machine-grid)" opacity=".3" pointerEvents="none"/>
      </svg>
      <span className="vb-ref-reactor-counter" role="status" aria-live="polite">
        <strong>{count}/3</strong> PRIVATE INPUTS RECEIVED
      </span>
    </div>
  );
}
