# Frontend dependency upgrade — Next.js 16, React 19, and ESLint 10

The frontend uses Next.js 16.4.6, React 19.3.1, matching React DOM 19.3.1,
matching TypeScript definitions 19.3.0, ESLint 10.15.0, and PostCSS 8.5.33.

## Runtime requirements

- Node.js `^22.13.0 || ^24.0.0`
- npm 10 or newer
- Next.js 16.4.6

## ESLint architecture

The project uses ESLint 10 with a direct-plugin flat configuration rather than
the aggregate `eslint-config-next` package.

The aggregate package brings `eslint-plugin-import`, `eslint-plugin-jsx-a11y`,
and `eslint-plugin-react` versions whose published peer ranges still exclude
ESLint 10. This caused the npm peer dependency warnings in the user's install.

The direct configuration avoids those unnecessary peer conflicts while
retaining:
- ESLint's recommended JavaScript rules through `@eslint/js`.
- Next.js recommended rules through `@next/eslint-plugin-next`.
- React Hooks recommended rules through `eslint-plugin-react-hooks`.
- TypeScript recommended rules through `typescript-eslint`.

The selected TypeScript ESLint and React Hooks packages declare ESLint 10
support. The project does not disable React Hooks lint rules.

## Health-check effect

The health-fetch helper no longer performs React state updates. The mount effect
uses its Promise callbacks to apply the response and uses an AbortController to
ignore late results after unmount. Manual refresh updates loading state from the
button event handler.

## Lockfile handling

The uploaded archive did not include `frontend/package-lock.json`. The user's
existing lockfile was generated with a different dependency graph and the
aggregate Next.js ESLint config. After extracting this update, regenerate the
lockfile with `npm install`, inspect `npm ls`, and then verify reproducibility
with `npm ci`.

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

## Next.js 16 migration notes

- `next lint` was removed; the `lint` script calls the ESLint CLI.
- The founder route awaits Promise-based App Router parameters on the server
  and passes resolved values to its client component.
- Docker frontend stages use Node 22 Alpine. Ensure the image tag resolves to
  Node 22.13 or newer.
- Next.js 16's `next build` does not run ESLint automatically. Keep lint as a
  separate release-gate command.
