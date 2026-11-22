"use client";

/** Purely presentational: this component never receives salaries or credentials. */
type Props = { submitted: ReadonlySet<number>; stage: string };

const PARTIES = [0, 1, 2] as const;

export default function ReactorStage({ submitted, stage }: Props) {
  const count = PARTIES.filter((id) => submitted.has(id)).length;
  const computing = stage === "computing";
  const completed = stage === "completed";
  const ready = stage === "ready" && count === 3;

  return (
    <div className={`r4-machine-scene ${computing ? "r4-machine--computing" : ""} ${completed ? "r4-machine--complete" : ""} ${ready ? "r4-machine--ready" : ""}`}>
      <span className="r4-scene-index" aria-hidden="true">0{count}<i> / 03</i></span>
      <div className="r4-scene-slash" aria-hidden="true" />
      <div className="r4-cartridge-row" role="list" aria-label="Founder submission status">
        {PARTIES.map((id) => {
          const loaded = submitted.has(id);
          return (
            <div key={id} className={`r4-cartridge-slot ${loaded ? "r4-cartridge-slot--loaded" : ""}`} role="listitem" aria-label={`Founder ${id + 1}: ${loaded ? "submission received and docked" : "awaiting private input"}`}>
              <span className="r4-slot-label">P{String(id + 1).padStart(2, "0")}</span>
              <div className="r4-cartridge" aria-hidden="true">
                <svg viewBox="0 0 220 86" focusable="false">
                  <path className="r4-cartridge-case" d="M24 4H196L216 43L196 82H24L4 43Z" />
                  <path className="r4-cartridge-fill" d="M28 12H192L208 43L192 74H28L12 43Z" />
                  <path className="r4-cartridge-edge" d="M31 12L17 43L31 74M189 12L203 43L189 74" />
                  <path className="r4-cartridge-band" d="M62 14V72M73 14V72" />
                  <path className="r4-cartridge-signal" d="M92 43H169" />
                  <path className="r4-cartridge-check" d="m106 43 12 11 23-25" />
                </svg>
              </div>
              <span className="r4-slot-status">{loaded ? "SEALED" : "AWAITING"}</span>
            </div>
          );
        })}
      </div>

      <svg className="r4-machine-body" viewBox="0 0 1000 310" role="img" aria-label={`${count} of 3 submissions received. Reactor ${computing ? "computing" : completed ? "completed" : ready ? "ready" : "waiting"}.`}>
        <path className="r4-machine-chassis" d="M74 73L122 27H878L926 73V258L880 299H120L74 258Z" />
        <path className="r4-machine-chassis-detail" d="M91 90H909M97 248H903M146 280H854" />
        {[160, 500, 840].map((x, i) => (
          <g key={x} className={submitted.has(i) ? "r4-machine-port r4-machine-port--active" : "r4-machine-port"}>
            <rect x={x - 89} y="12" width="178" height="63" rx="6" className="r4-port-mouth" />
            <path d={`M${x - 66} 85H${x + 66}`} className="r4-port-indicator" />
            <path d={`M${x} 92V136`} className="r4-port-cable" />
          </g>
        ))}
        <path className="r4-machine-feed" d="M160 136H500M840 136H500M500 136V162" />
        <path className="r4-machine-crossbar" d="M125 211H377M623 211H875" />
        <g className="r4-machine-ring" transform="translate(500 204)">
          <circle r="91" className="r4-core-outer" />
          <g className="r4-core-rotor">
            <circle r="76" className="r4-core-track" />
            <path d="M-76 0h24M52 0h24M0 -76v24M0 52v24" className="r4-core-ticks" />
          </g>
          <circle r="56" className="r4-core-center" />
          <path d="M0 -29L27 0L0 29L-27 0Z" className="r4-core-diamond" />
          <path d="M-13 0H13M0 -13V13" className="r4-core-cross" />
        </g>
        <path className="r4-machine-base" d="M360 288H640" />
      </svg>
      <span className="r4-machine-footnote" aria-hidden="true">SECURE COMPUTATION / THREE-PARTY PROTOCOL</span>
    </div>
  );
}
