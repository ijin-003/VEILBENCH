# Frontend toolchain follow-up — React 19, ESLint 10, and health-check effect

This follow-up addresses the Windows verification output after the Next.js 16.4.6
migration.

## Changes

- React and React DOM are pinned together to 19.3.1.
- React and React DOM TypeScript definitions are pinned together to 19.3.0.
- ESLint remains on 10.15.0, the current supported major line.
- The frontend no longer installs `eslint-config-next`, because that aggregate
  config brings plugins whose declared ESLint peer ranges still stop at ESLint 9.
- Next.js lint rules are loaded directly from `@next/eslint-plugin-next@16.4.6`,
  following the official Next.js guidance for avoiding conflicting plugin stacks.
- React Hooks rules are loaded from `eslint-plugin-react-hooks@7.1.1`, which
  supports ESLint 10.
- TypeScript rules are loaded from `typescript-eslint@8.73.0`, which supports
  ESLint 10.
- `@eslint/js@10.0.1` supplies the ESLint recommended JavaScript rules.
- PostCSS remains pinned to 8.5.33.
- Node engine support remains `^22.13.0 || ^24.0.0`.

## Health-check effect correction

The health request is now a state-free helper that only performs the HTTP request
and returns the parsed health payload. The mount effect invokes that helper and
updates React state only in asynchronous Promise callbacks. It uses an
`AbortController` to ignore late responses after unmount.

Manual refresh uses a separate event-handler callback, where setting the loading
state is appropriate. The React Hooks lint rule is not disabled.

## Lockfile handling

The uploaded source archive did not contain `frontend/package-lock.json`. The
previous lockfile on the user's computer was generated for a dependency graph
that included `eslint-config-next` and ESLint 10, which produced peer warnings.
Do not reuse that old lockfile unchanged.

After applying this update, regenerate the lockfile once with `npm install`.
Then use `npm ci` to confirm a clean, reproducible install. Keep the generated
lockfile with the project and commit it with the matching package manifest.

## Required verification

```powershell
cd frontend
npm install
npm ls eslint @eslint/js @next/eslint-plugin-next eslint-plugin-react-hooks typescript-eslint react react-dom
npm audit
npm audit --omit=dev
npm run lint
npm run typecheck
npm run build
npm ci
```

The install should not report ERESOLVE peer overrides. If npm still reports a
peer conflict, capture the full `npm ls` output before changing versions.

## Runtime notes

- Node 24.11.1 is accepted by the package engine declaration.
- The production Dockerfile remains on Node 22 Alpine; use a Node 22 image at
  least 22.13 for the ESLint toolchain.
- No lint rule has been disabled or suppressed.
