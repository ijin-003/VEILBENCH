# VEILBENCH — Final Demonstration and Viva Plan

**State:** Phase F teaching/demo outline; use synthetic inputs only.  
**Presentation content should be reconciled with the actual university rubric before submission.**  
**Demo target:** [VEILBENCH live frontend](https://veilbench.vercel.app).

## Recommended 10-slide structure

| Slide | Topic | What to show | What to say |
|---|---|---|---|
| 1 | Title & research problem | VEILBENCH title, team names and problem statement | Ordinary salary surveys reveal each person's salary to the central collector |
| 2 | Project objectives | Three-party sum/average, direct submission, authenticated management | We demonstrate MPC with an honest accounting of deployment limitations |
| 3 | System architecture | Diagram from `PHASE_F_ACADEMIC_TECHNICAL_REPORT.md` | Next.js on Vercel; FastAPI coordinator and 3 party apps share Render; Neon stores metadata/results |
| 4 | Shamir secret sharing | `f(x)=s+ax mod p`, three shares, threshold `t=1` | One share cannot reconstruct a private input under the independent passive-party model |
| 5 | Data lifecycle | Admin invite → activation → 3 inputs → ready → compute → aggregate | Salary input is sent to the assigned party, not to the coordinator salary route |
| 6 | Live product | Login, Session Tools, Account Directory, live countdown, reactor | Only session/account metadata and submission receipts appear in admin controls |
| 7 | Correctness experiment | Synthetic inputs 50k/70k/60k → 180k sum and 60k average | The real 3-party MPyC protocol was exercised by isolated CI and a reported hosted demo |
| 8 | Security evaluation | Nine attack-lab categories; redacted evidence board | Wrong roles/tokens and duplicate submissions are rejected; no claim of malicious security |
| 9 | Performance & reliability | Two CI median results (179.73 ms / 242.20 ms); failure/recovery tests | Local subprocess benchmarks are not hosted response times; hosted timings remain pending |
| 10 | Limitations & future work | Shared-host caveat, separate operators, improved identity model | Real salary privacy cannot be promised on one shared cloud operator; synthetic demonstration only |

## Instructor-facing live demo (safe sequence)

1. Open the main page and explain coordinator/three logical party architecture.
2. Sign in as admin, open **Session Tools**, review account and session listings, and point out one live countdown. Do not display usernames from private real users; create synthetic demo accounts.
3. Create one **fresh** 30-minute session. Keep invitation strings away from the projector and screenshots.
4. Invite three fictitious founders, each with a different login username and party assignment.
5. In separate clean browser sessions, activate accounts and show the password-strength/matching UI. Avoid putting real passwords on the projector.
6. Submit synthetic salaries **50,000**, **70,000**, **60,000**, one per party.
7. On the admin screen, show only the **three input-received indicators**; trigger compute once.
8. Verify the public **sum = 180,000** and **average = 60,000**. Refresh result from a fresh admin read to demonstrate persistence.
9. Explain the security lab from **offline CI artifacts**. Do not perform live denial-of-service, brute-force or party interruption.
10. Close with the shared Render-host operator limitation and intended future deployment improvements.

### Live demo fallbacks

- If Render takes time to wake, show the authenticated local CI acceptance artifact rather than guessing a latency result.
- If a hosted party restarts mid-session, disclose the failure, abandon the interrupted session and create a fresh synthetic one.
- If the external internet is unavailable, use **redacted** screenshots and the previously generated CI evidence artifacts; label them as archived.
- Never embed live invitation tokens, credentials, bearer headers or real salary amounts in slides or screenshots.

## Likely viva questions and short defensible answers

**Q. Why MPC rather than encrypting the values in a database?**  
A. Database encryption protects storage, but the ordinary application still decrypts the values to compute. MPC enables a secure computation across separate party-held shares under the appropriate trust model. Our current demonstration does not independently host those parties.

**Q. What is the threshold?**  
A. Three parties are configured with threshold one (`m=3,t=1`); in Shamir sharing, one share does not reveal the secret, while a degree-one polynomial is reconstructible from two shares. This is a mathematical sharing property, not the demonstrated availability of the whole protocol with a missing third participant.

**Q. Does the coordinator see salary inputs?**  
A. It has no plain-salary input route and its session database stores metadata and final aggregates. A privileged operator of our shared container could still inspect all party processes, which is outside the demonstrated confidential boundary.

**Q. Why only three founders?**  
A. The current application and runtime are deliberately fixed to exactly three parties. Expanding cohorts requires changes to protocol configuration, application account/session models and the privacy interpretation.

**Q. What happens if one party is offline?**  
A. The local missing-party test demonstrates the computation does not complete in its bounded observation window. It does not prove automatic tolerance or uninterrupted availability.

**Q. Are tokens unique people?**  
A. No. Login usernames currently identify accounts, while short-lived invitation and bearer tokens grant scoped access. A future architecture can add permanent UUID account identifiers and duplicate display names, without confusing identity with a credential.

**Q. Is the password indicator a formal strength estimator?**  
A. No. It is a lightweight local quality cue with length/common-pattern checks; backend enforces minimum length and rejects certain obvious patterns. It is not a guarantee that a password is safe or uncompromised.

**Q. What does the measured 179.73 ms mean?**  
A. It is the median *local three-subprocess MPyC computation* on one GitHub Actions worker. Another run produced a 242.20 ms median. Neither represents the hosted Vercel–Render request duration.

**Q. Can the deployed system safely process real salaries?**  
A. No. The three logical MPC parties share a hosting operator and infrastructure. We explicitly restrict the current hosted prototype to synthetic academic data.

## Before presenting

- [ ] Confirm university rubric/title, authors, supervisor and submission formatting.
- [ ] Confirm admin account and active-session directories work in the *current* deployed UI, not only Vercel's build preview.
- [ ] Obtain **redacted** screenshot of landing, admin session list/timer, accounts list, founder submitted view, final aggregate.
- [ ] Collect three numeric `Server-Timing` readings from separate synthetic hosted sessions if the report requires hosted latency.
- [ ] Open and verify CI artifacts (acceptance, performance, security) before presenting.
- [ ] Verify demo test accounts are disposable; no real people's salary or credentials.
- [ ] State all three shared-host trust caveats explicitly (one operator, process-memory access, no independent operator network trust).
