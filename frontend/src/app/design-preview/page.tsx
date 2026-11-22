import { notFound } from "next/navigation";
import Link from "next/link";
import { LockKeyhole, ArrowRight, CheckCircle2 } from "lucide-react";
import ReactorStage from "../ReactorStage";
import ApprovedResultArt from "../ApprovedResultArt";
import { PrivateMark } from "../submit/[sessionId]/[partyId]/FounderSubmissionForm";
import "../approved-board.css";

/**
 * Read-only visual gallery for review deployments only.
 * Production returns 404. No tokens, salary requests, API calls or real sessions.
 */
export default function DesignPreviewPage() {
  if (process.env.VERCEL_ENV !== "preview" && process.env.NODE_ENV !== "development") notFound();

  return (
    <main className="vb-review-gallery">
      <header className="vb-review-top">
        <strong>VEILBENCH <b>//</b></strong>
        <span>DESIGN REVIEW / PREVIEW ONLY</span>
        <Link href="/">BACK TO SITE <ArrowRight size={16}/></Link>
      </header>
      <p className="vb-review-notice">VISUAL-ONLY MOCK DATA — NO AUTHENTICATION OR COMPUTATION IS PERFORMED ON THIS PAGE.</p>
      <nav className="vb-review-jump" aria-label="Preview screens">
        <a href="#reactor">01 / REACTOR</a>
        <a href="#founder">02 / FOUNDER</a>
        <a href="#result">03 / RESULTS</a>
      </nav>
      <section id="reactor" className="vb-review-section">
        <header className="vb-review-label"><span>01</span><h2>ADMIN / REACTOR</h2><small>ALL THREE SUBMISSIONS CONFIRMED — ILLUSTRATIVE ONLY</small></header>
        <div className="r4-reactor-root vb-review-reactor">
          <div className="r4-reactor-layout">
            <div className="r4-reactor-head">
              <div><span className="r4-kicker">THREE-FOUNDER SECURE COMPUTATION / 03</span><h1>MPC <em>REACTOR.</em></h1></div>
              <div className="r4-reactor-actions"><span className="r4-link r4-link--online"><i/> MOCK STATUS</span><span className="r4-tools">SESSION TOOLS</span></div>
            </div>
            <section className="r4-reactor-view" aria-label="Animated illustrative MPC chamber"><ReactorStage submitted={new Set([0,1,2])} stage="ready" /></section>
            <div className="r4-reactor-command">
              <div className="r4-reactor-status"><span className="r4-status-eyebrow">ILLUSTRATIVE STATE</span><strong>ALL CARTRIDGES DOCKED</strong></div>
              <div className="r4-command-buttons"><span className="r4-primary vb-review-button-faux">COMPUTE <ArrowRight size={22}/></span></div>
            </div>
            <p className="r4-privacy"><LockKeyhole size={14}/> No real submissions. No credentials or individual salaries.</p>
          </div>
        </div>
      </section>
      <section id="founder" className="vb-review-section">
        <header className="vb-review-label"><span>02</span><h2>FOUNDER / PRIVATE SUBMISSION</h2><small>INPUT FORM ILLUSTRATION — SUBMISSION DISABLED</small></header>
        <div className="d4-root vb-review-founder">
          <section className="d4-art" aria-label="Private channel illustration">
            <div className="d4-art-head">VEILBENCH <span>//</span> PRIVATE / 01</div>
            <PrivateMark active={false} sending={false} sealed={false} partyId="0"/>
            <div className="d4-art-foot">CONFIDENTIAL <span>—</span> SINGLE USE</div>
          </section>
          <section className="d4-work">
            <div className="d4-work-top">PARTY 01 <span>DIRECT MPC CHANNEL</span></div>
            <div className="d4-work-content">
              <span className="d4-kicker">01 / PRIVATE INPUT</span>
              <h1>SUBMIT YOUR <em>SALARY.</em></h1>
              <p className="d4-intro">YOUR VALUE REMAINS PRIVATE.</p>
              <div className="d4-form">
                <label htmlFor="vb-review-salary">SALARY AMOUNT <span>WHOLE NUMBER</span></label>
                <input id="vb-review-salary" disabled placeholder="Enter your salary" aria-label="Illustrative disabled salary field"/>
                <span className="d4-submit vb-review-button-faux"><LockKeyhole size={22}/> SEAL & SUBMIT <ArrowRight size={22}/></span>
              </div>
              <p className="d4-privacy"><LockKeyhole size={17}/> This design-only gallery cannot submit data.</p>
            </div>
            <div className="d4-work-bottom">PRIVATE DEPOSIT <span>///</span> VEILBENCH</div>
          </section>
        </div>
      </section>
      <section id="result" className="vb-review-section">
        <header className="vb-review-label"><span>03</span><h2>RESULT / REVEAL</h2><small>PUBLIC AGGREGATE ONLY — SYNTHETIC EXAMPLE</small></header>
        <div className="r4-reactor-root vb-review-result">
          <section className="r4-results vb-board-results" aria-label="Illustrative computed aggregate">
            <div className="vb-board-results-art" aria-hidden="true"><ApprovedResultArt /></div>
            <div className="vb-board-results-data">
              <h2>COMPUTATION COMPLETE.</h2>
              <p>AGGREGATE RESULTS ONLY</p>
              <div className="vb-board-result-row"><small>TOTAL / SUM</small><strong>180,000</strong></div>
              <div className="vb-board-result-row"><small>AVERAGE</small><strong>60,000</strong></div>
              <span className="vb-board-results-note">THREE FOUNDERS. ONE SHARED RESULT. NO INDIVIDUAL SALARIES REVEALED.</span>
            </div>
          </section>
        </div>
      </section>
      <footer className="vb-review-footer"><CheckCircle2 size={17}/> DESIGN CONCEPTS ONLY. THE LIVE AUTHENTICATED FLOW REMAINS UNCHANGED.</footer>
    </main>
  );
}
