# Hosted computation timing — Phase C protocol

The authenticated coordinator `POST /api/v1/sessions/{session_id}/compute`
endpoint includes a `Server-Timing: coordinator-compute;dur=<milliseconds>`
response header **on successful computation**.

This timer starts inside the authenticated endpoint and ends after coordinator
status checks, distributed MPyC execution, cleanup and result persistence.
It does **not** measure founder onboarding, browser-to-Render network latency,
or Render cold starts. Request timings displayed by browser DevTools give a
separate client-observed HTTP duration and may include network overhead.

## Safe measurement

1. Use a fresh disposable three-founder benchmark with synthetic salaries
   (e.g. 50,000; 70,000; 60,000). Never use real salary information.
2. In the administrator's browser, open Developer Tools → Network. Perform
   the normal founder submissions and click Compute exactly once.
3. Select the successful `POST /api/v1/sessions/.../compute` request. Record
   only the `Server-Timing` duration and the request's full elapsed time
   from the Timing pane. **Do not record or share Authorization headers,
   invitation tokens, cookies, session IDs, or salary submissions.**
4. Confirm the returned public aggregate is 180,000 and average is 60,000.
5. Repeat using **new sessions** at least three times, when convenient. Mark
   cold-start versus already-awake Render separately. Do not repeatedly run
   active computations or stress Render Free.
6. Correlate the timestamp with Render CPU/memory telemetry. One-minute samples
   are not guaranteed to capture the short-lived MPyC worker RSS peak.

Use the real observed numbers in the final evaluation; the earlier GitHub
Actions median ~215 ms is a **local subprocess baseline**, not a hosted
end-to-end timing. Do not infer timing from Render response log timestamps.

## Safety and scope

The Server-Timing field reports only a numeric elapsed time; it never contains
private input, tokens, usernames, or session IDs. Existing authentication,
role restrictions and MPC session handling are unchanged. On errors the
endpoint does not publish a misleading successful-compute duration.

The deployed academic architecture has three logical parties in a single
Render container. It must continue to be used with synthetic salaries only.
