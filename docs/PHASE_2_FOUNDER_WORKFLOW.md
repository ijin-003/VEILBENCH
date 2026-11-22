# VEILBENCH Phase 2 — Three-founder workflow

## Final academic-demo flow

1. An administrator authenticates to the coordinator using the management token.
2. The coordinator creates a metadata-only benchmark session and issues three short-lived,
   party-scoped founder capabilities.
3. Founder 1 opens the Party 0 invitation page, Founder 2 opens Party 1, and Founder 3 opens
   Party 2. Each founder receives the submission URL and one-time capability separately.
4. Each browser sends its salary directly to its assigned party's HTTPS `/sessions/{id}/input`
   endpoint. The coordinator has no salary-submission route and does not proxy these requests.
5. The coordinator polls only the three party status endpoints. It marks the session ready only
   after all three parties confirm `input_submitted=true` in an admissible state.
6. The administrator may initiate computation only when the session is `ready` and all three
   party IDs are present.
7. Each party starts the MPyC protocol. The coordinator receives only the reconstructed aggregate
   and average, verifies the three party responses agree, and stores those aggregate results.
8. The dashboard displays the aggregate and average, never individual founder salaries.

## Browser and CORS configuration

The frontend uses these build-time public variables:

- `NEXT_PUBLIC_API_URL`: public HTTPS URL of the FastAPI coordinator.
- `NEXT_PUBLIC_PARTY_0_URL`: public HTTPS URL for Party 0.
- `NEXT_PUBLIC_PARTY_1_URL`: public HTTPS URL for Party 1.
- `NEXT_PUBLIC_PARTY_2_URL`: public HTTPS URL for Party 2.

The coordinator uses:

- `FRONTEND_PUBLIC_URL`: public frontend origin used when constructing founder links.
- `ALLOWED_ORIGINS`: must include the exact frontend origin.
- `MPC_PARTY_PUBLIC_URLS`: exactly three distinct public party base URLs, in party-ID order.

Each party uses `MPC_PARTY_ALLOWED_ORIGINS`, which must include the frontend origin so the
founder browser can make its direct cross-origin submission. The browser requests use
`credentials: omit`; the founder capability is sent in the Authorization header. Do not put
capabilities in query strings or URLs.

For production, all browser-facing URLs must use publicly trusted HTTPS certificates. The local
development CA is not suitable for public browsers. Do not place secrets in any `NEXT_PUBLIC_*`
variable. Management credentials and party control credentials remain server-side only.

## Polling and disclosure

The management dashboard polls the coordinator's metadata-only session endpoint every four
seconds while the session is active. It does not poll party endpoints from the browser and does
not receive founder salary values. The compute button is enabled only for a `ready` session with
all three submitted party IDs. The backend independently enforces the same gate.

The create-session response contains the three short-lived capabilities. It is marked
`Cache-Control: no-store` and `Pragma: no-cache`. Administrators should distribute each link and
its matching capability separately and only to its intended founder.

## Academic deployment limitation

The initial academic deployment runs the coordinator and three party containers on one VPS.
This demonstrates the three-party MPyC protocol and the direct-input application workflow, but it
does not provide independent administrative trust between parties. A VPS administrator can
control all three party processes. This limitation must be stated in the project demonstration.

## Verification boundary

Automated backend tests verify the API contract, party-scoped capabilities, status metadata,
no-store invite response headers, and coordinator-side absence of a salary submission endpoint.
A live end-to-end release check must additionally verify browser CORS and trusted TLS, all three
party containers, PostgreSQL persistence, and a real MPyC computation using three independent
founder browser sessions.
