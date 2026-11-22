"use client";

/**
 * Pure presentation: displays only the submitted party IDs and the coordinator's
 * session state. No salary values, capability tokens, or invitation URLs enter
 * this component.
 */
type Props = {
  submitted: ReadonlySet<number>;
  stage: string;
};

const SLOTS = [
  { partyId: 0, x: 387, label: "01" },
  { partyId: 1, x: 600, label: "02" },
  { partyId: 2, x: 813, label: "03" },
] as const;

export default function ReactorStage({ submitted, stage }: Props) {
  const running = stage === "computing";
  const complete = stage === "completed";
  const armed = stage === "ready" && submitted.size === 3;
  const allLoaded = submitted.size === 3;

  return (
    <div className={`rx-scene ${running ? "rx-scene--running" : ""} ${complete ? "rx-scene--complete" : ""} ${armed ? "rx-scene--armed" : ""} ${allLoaded ? "rx-scene--loaded" : ""}`}>
      <svg
        viewBox="0 0 1200 585"
        className="rx-svg"
        role="img"
        aria-label={`${submitted.size} of 3 partner inputs received. Reactor is ${running ? "computing" : complete ? "complete" : armed ? "ready" : "waiting"}.`}
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="rx-obsidian" x1="0" y1="0" x2="1" y2="1">
            <stop stopColor="#373039" />
            <stop offset=".26" stopColor="#1d171d" />
            <stop offset=".68" stopColor="#0a0a10" />
            <stop offset="1" stopColor="#3e2b35" />
          </linearGradient>
          <linearGradient id="rx-steel" x1="0" y1="0" x2="1" y2=".3">
            <stop stopColor="#f8e9dd" stopOpacity=".95" />
            <stop offset=".12" stopColor="#967b82" />
            <stop offset=".3" stopColor="#2b262e" />
            <stop offset=".64" stopColor="#70545f" />
            <stop offset=".9" stopColor="#251d27" />
            <stop offset="1" stopColor="#e2b5b0" />
          </linearGradient>
          <linearGradient id="rx-glass" x1="0" x2="1" y1="0" y2="0">
            <stop stopColor="#e5d7d7" stopOpacity=".38" />
            <stop offset=".20" stopColor="#111419" stopOpacity=".4" />
            <stop offset=".58" stopColor="#1b131c" stopOpacity=".75" />
            <stop offset=".81" stopColor="#c6aaaa" stopOpacity=".15" />
            <stop offset="1" stopColor="#fcebdc" stopOpacity=".68" />
          </linearGradient>
          <linearGradient id="rx-energy" x1="0" y1="0" x2="1" y2="1">
            <stop stopColor="#ffb48b" />
            <stop offset=".45" stopColor="#ec2449" />
            <stop offset="1" stopColor="#6a0826" />
          </linearGradient>
          <radialGradient id="rx-core-gradient">
            <stop stopColor="#fff0d9" />
            <stop offset=".16" stopColor="#ff8b7a" />
            <stop offset=".34" stopColor="#eb2549" />
            <stop offset=".72" stopColor="#620b28" />
            <stop offset="1" stopColor="#150d17" />
          </radialGradient>
          <filter id="rx-halo" x="-80%" y="-80%" width="260%" height="260%">
            <feGaussianBlur stdDeviation="15" />
          </filter>
          <pattern id="rx-microgrid" patternUnits="userSpaceOnUse" width="23" height="23">
            <path d="M23 0H0V23" fill="none" stroke="#7f656f" strokeOpacity=".17" strokeWidth=".8" />
          </pattern>
          <clipPath id="rx-pod-window">
            <path d="M-28 -44L28 -44L35 -24V47L28 66H-28L-35 47V-24Z" />
          </clipPath>
        </defs>

        {/* Room / negative space: graphic-novel industrial drafting marks. */}
        <path d="M30 52H247M30 52V160M1170 52H950M1170 52V160M30 531H240M30 531V441M1170 531H960M1170 531V441" fill="none" stroke="#695560" strokeOpacity=".64" strokeWidth="1.5" />
        <path d="M128 455L245 455M952 455H1073M127 460H200M1001 460H1072" stroke="#e83e57" strokeOpacity=".3" strokeWidth="2" />
        <path d="M280 85L600 24L920 85" stroke="#7d6570" strokeWidth="1" fill="none" opacity=".35" />
        <path d="M600 24V88" stroke="#7d6570" strokeOpacity=".4" strokeDasharray="3 10" />

        {/* Reactor shadow and frame: a single object, not three competing cards. */}
        <ellipse cx="600" cy="537" rx="365" ry="29" fill="#000" opacity=".53" />
        <g className="rx-machine">
          <path d="M259 262L306 223H894L941 262L965 466L911 523H289L235 466Z" fill="#100d14" stroke="#5e4853" strokeWidth="3" />
          <path d="M285 270L323 245H877L915 270L939 449L895 498H305L261 449Z" fill="url(#rx-obsidian)" stroke="#b29492" strokeOpacity=".74" strokeWidth="2.5" />
          <path d="M316 284H884L908 453H291Z" fill="url(#rx-microgrid)" opacity=".62" />
          <path d="M271 295H932M271 463H932" stroke="#dba89a" strokeOpacity=".36" strokeWidth="2" />
          <path d="M274 309L238 336V430L270 458M926 309L963 336V430L931 458" fill="#392631" stroke="#aa7e7e" strokeWidth="2" />
          <path d="M289 482H911L887 512H313Z" fill="#181018" stroke="#74545d" strokeWidth="2" />
          <path d="M325 505H875" stroke="#f24b58" strokeOpacity=".75" strokeWidth="4" />
          {/* Decorative side warning slashes, tightly restrained. */}
          {[0, 1, 2].map((n) => (
            <g key={`stripe-${n}`}>
              <path d={`M${283 + n * 18} 389l-12 27M${893 + n * 18} 389l-12 27`} stroke="#e24b59" strokeWidth="4" strokeOpacity=".8" />
            </g>
          ))}
          <path d="M357 337L407 355M843 337L793 355" stroke="#f0dacf" strokeOpacity=".25" strokeWidth="8" />

          {/* Routes converge on one sealed computation core. */}
          <path className={`rx-route ${submitted.has(0) ? "rx-route--active" : ""}`} d="M387 285V343Q387 366 464 396" />
          <path className={`rx-route ${submitted.has(1) ? "rx-route--active" : ""}`} d="M600 285V352" />
          <path className={`rx-route ${submitted.has(2) ? "rx-route--active" : ""}`} d="M813 285V343Q813 366 736 396" />

          {/* Retaining ring and reactor. */}
          <g transform="translate(600 398)">
            <circle className="rx-aura" r="100" fill="#ed2448" opacity=".15" filter="url(#rx-halo)" />
            <circle r="132" fill="#0a0a0e" stroke="#59414c" strokeWidth="12" />
            <circle r="117" fill="none" stroke="#ddae9e" strokeWidth="2" strokeDasharray="2 11" opacity=".65" />
            <g className="rx-outer-rotor">
              <circle r="105" fill="none" stroke="#e74a5c" strokeWidth="7" strokeDasharray="40 23 78 20 32 35" />
              <path d="M-8 -127h16l8 29h-32ZM-8 127h16l8 -29h-32ZM-127 -8v16l29 8v-32ZM127 -8v16l-29 8v-32Z" fill="#e9d8c8" />
            </g>
            <g className="rx-inner-rotor">
              <circle r="91" fill="none" stroke="#9c6a76" strokeWidth="4" strokeDasharray="11 10 5 28" />
              <path d="M-58 -58L0 -83L58 -58L83 0L58 58L0 83L-58 58L-83 0Z" fill="none" stroke="#d9a9a0" strokeWidth="2" strokeOpacity=".85" />
            </g>
            <circle r="77" fill="#0a070d" stroke="#552b3c" strokeWidth="6" />
            <circle className="rx-true-core" r="62" fill={allLoaded ? "url(#rx-core-gradient)" : "#281620"} stroke={allLoaded ? "#ffe3cd" : "#8b6a72"} strokeWidth="2.5" />
            <circle r="44" fill="none" stroke="#f0c1af" strokeOpacity={allLoaded ? ".9" : ".3"} strokeWidth="1" strokeDasharray="3 7" />
            <path d="M0 -29L24 -14V15L0 31L-24 15V-14Z" fill="none" stroke="#fff0de" strokeOpacity={allLoaded ? "1" : ".5"} strokeWidth="3" />
            <circle r="7" fill={allLoaded ? "#fff1dc" : "#5f4551"} />
            <g className="rx-reactor-shutters">
              <path d="M-93 -52L-44 -20V21L-93 55Z" fill="url(#rx-steel)" stroke="#f4a3a2" strokeWidth="1.5" />
              <path d="M93 -52L44 -20V21L93 55Z" fill="url(#rx-steel)" stroke="#f4a3a2" strokeWidth="1.5" />
            </g>
          </g>
        </g>

        {/* Three glass cartridges with metal retaining bands. */}
        {SLOTS.map(({ partyId, x, label }) => {
          const loaded = submitted.has(partyId);
          return (
            <g key={partyId} className={loaded ? "rx-slot rx-slot--loaded" : "rx-slot"}>
              <title>{`Partner ${partyId + 1}: ${loaded ? "submission received, cartridge docked" : "awaiting private submission"}`}</title>
              <text x={x} y="11" fill="#b7a0a2" fontSize="11" textAnchor="middle" fontWeight="800" letterSpacing="4">PARTY {label}</text>
              <text x={x} y="30" fill={loaded ? "#f1daca" : "#907780"} fontSize="10" textAnchor="middle" fontWeight="800" letterSpacing="2.4">{loaded ? "SEALED" : "AWAITING"}</text>
              <path d={`M${x} 91V213`} stroke="#5d454f" strokeDasharray="2 10" strokeWidth="2" />
              <path d={`M${x - 54} 222l15 -21h78l15 21v30h-108z`} fill="#0a090f" stroke="#785661" strokeWidth="2" />
              <path d={`M${x - 44} 227h88v15h-88z`} fill={loaded ? "#a8213b" : "#2c212b"} stroke={loaded ? "#ffb2a8" : "#67515b"} strokeWidth="2" />
              <rect className="rx-dock-light" x={x - 27} y="246" width="54" height="8" rx="3" fill={loaded ? "#f95567" : "#3c2833"} />
              <g transform={`translate(${x} 130)`}>
                <g className={loaded ? "rx-cartridge rx-cartridge--inserted" : "rx-cartridge rx-cartridge--idle"}>
                  <path d="M-32 -50L-21 -62H21L32 -50V72L20 86H-20L-32 72Z" fill="url(#rx-steel)" stroke="#f9dbcd" strokeOpacity=".9" strokeWidth="2" />
                  <path d="M-28 -41L-19 -50H19L28 -41V55L19 67H-19L-28 55Z" fill="url(#rx-glass)" stroke="#c4a2a4" strokeOpacity=".65" strokeWidth="2" />
                  <g clipPath="url(#rx-pod-window)">
                    <rect x="-30" y={loaded ? "-40" : "13"} width="60" height={loaded ? "115" : "55"} fill={loaded ? "url(#rx-energy)" : "#51303e"} opacity={loaded ? ".95" : ".43"} className="rx-liquid" />
                    <path d="M-17 -36V50" stroke="#fff1dc" strokeOpacity=".3" strokeWidth="4" />
                    <path className="rx-scanner" d="M-24 12H24" stroke="#ffe8d8" strokeWidth="2" />
                  </g>
                  <path d="M-42 -50H42L35 -32H-35ZM-38 66H38L31 85H-31Z" fill="#e2b4ac" stroke="#271b22" strokeWidth="2" />
                  <path d="M-42 -50H42L35 -42H-35Z" fill="#fff1e3" opacity=".67" />
                  <path d="M-40 -50V74M40 -50V74" stroke="#7d5865" strokeWidth="4" />
                  <path d="M-11 -71L11 -71L21 -62H-21Z" fill="#e84257" stroke="#fdc0b1" strokeWidth="2" />
                  <circle r="8" cy="4" fill={loaded ? "#ffe9d6" : "#1a1018"} stroke="#eeded0" strokeWidth="1.5" />
                  <path d="M-10 31H10M-10 37H10" stroke="#f2ded3" strokeOpacity=".55" />
                </g>
              </g>
              <g className="rx-loaded-mark" opacity={loaded ? "1" : "0"}>
                <path d={`M${x - 15} 219l9 9 22 -23`} fill="none" stroke="#fff0dd" strokeWidth="4" strokeLinecap="round" />
              </g>
            </g>
          );
        })}

        {/* Output rail hints at where the eventual result emerges. */}
        <path d="M520 530H680" stroke="#9a7278" strokeOpacity=".6" strokeWidth="2" />
        <path d="M560 542H640" stroke="#e84958" strokeOpacity=".8" strokeWidth="3" />
        <path d="M590 552l10 10 10 -10" fill="none" stroke="#e84958" strokeWidth="2" />
        <text x="600" y="580" fill="#9b8088" textAnchor="middle" fontSize="10" fontWeight="800" letterSpacing="2.4">AGGREGATE OUTPUT</text>
      </svg>
      <div className="rx-legend" aria-hidden="true">
        <span>INPUT / SEALED</span>
        <span className="rx-legend-line" />
        <span>CORE / {running ? "ACTIVE" : complete ? "RELEASED" : armed ? "READY" : "STANDBY"}</span>
      </div>
    </div>
  );
}
