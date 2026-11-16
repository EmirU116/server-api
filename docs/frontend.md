# Frontend development (React, TypeScript, Vite)

The frontend is a local React application under `frontend/`. Backend development
is deferred while this interface is developed. The FastAPI foundation is
unchanged; its business endpoints are not implemented yet.

## Run locally (Node.js, npm)

Use Node.js 22.12 or newer in the Node 22 release line, or a newer supported
Node release. From the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173>. Stop the server with `Ctrl+C`.
The committed `package-lock.json` records the installed dependency versions;
use `npm ci` for subsequent clean installations from that lockfile.
Node/Vite are frontend development tools; the application backend remains Python.

## Available views (React, TypeScript, CSS)

| View | Implemented interface |
| --- | --- |
| Overview | CPU/memory/disk cards, open incident count, utilization chart, server/database health, recent incidents, server summary |
| Metrics | Chart ranges relative to the newest sample, toggles for each metric, hover values, paginated table of loaded measurements |
| Server details | Server display name, hostname, OS, architecture, stable ID, health and reported uptime |
| Incidents | Search, status filters, record details, create/edit forms, resolution/reopening, and deletion confirmation |

The layout adapts to narrow screens with a horizontal navigation menu and
scrollable data tables. Forms use native dialogs, labeled inputs, required
fields, length limits, and non-future occurrence times. Focus styles, a skip
link, reduced-motion support, and a text table alternative to charts are present.
Actual browser layout, keyboard behavior, and assistive technology compatibility
still require browser review.

## Demo workspace (TypeScript)

Demo mode is the default and is labeled throughout the interface. Fixed sample
metrics and server identity come from `frontend/src/services/demo.ts`; they are
not measurements of this computer or a deployed EC2 server. No API connection
is attempted on startup.

Incident edits are held only in React memory. Reloading the page or switching
back to demo mode resets them. Refresh in demo mode explains that samples are
fixed and preserves current incident edits; it does not manufacture new readings.
The demo is available without running Python or PostgreSQL.

## API workspace (TypeScript, HTTP)

Select **Connect API** and supply a bearer token. The token is kept in memory,
cleared on reload or return to demo mode, and never put in local storage or a
`VITE_*` build variable. Do not put real tokens in tracked files.

The client in `frontend/src/services/api.ts` follows [the API contract](api.md):

- Reads public health and authenticated server, metrics, and incident endpoints.
- Sends POST/PATCH/DELETE for incident changes; administrator permission will
  be enforced by the future backend. Permission failures are shown in the UI.
- Uses same-origin `/api/v1` paths. The Vite development proxy forwards `/api`
  to `http://127.0.0.1:8000`, avoiding a backend CORS change.
- Applies a request timeout, validates response shapes before rendering, and
  shows safe error messages for connection, authentication, permission,
  validation, and server failures. A structured unhealthy health response with
  HTTP 503 is displayed as unhealthy.
- Loads the latest 100 metrics and incidents. Incident search/status filters and
  metric table pagination apply to loaded records; the UI discloses truncated
  incident lists. Fetching further server-side pages is future work.
- Fetches on connection or explicit refresh. There is no automatic polling.

API mode never silently substitutes demo data. An initial load requires all
four read endpoints; if one fails, the workspace displays an error with retry
and return-to-demo actions. The current FastAPI foundation will return missing
route errors, so live integration cannot be verified yet.

Production hosting and same-origin `/api` reverse proxy configuration remain
future infrastructure work. `npm run preview` previews static build output;
the development-only API proxy is not a production deployment configuration.

## Verification (TypeScript, Vitest, Prettier)

Run inside `frontend/`:

```bash
npm run typecheck
npm test
npm run build
npm run format:check
```

`npm run format` applies readable multiline formatting. Tests use Vitest,
Testing Library, and jsdom. They exercise navigation, measurement pagination,
incident search/filtering/CRUD, input validation, demo/live separation, API
paths and headers, HTTP failures, response validation, and resolution timestamps.
Tests use dummy tokens and simulated responses, with no live server or database.
Native dialog methods are stubbed in jsdom, so these tests do not prove browser
focus trapping or visual layout.

The production build is emitted to ignored `frontend/dist/`. Google Fonts is
used for typography with system font fallbacks if unavailable. No screenshots,
assets, credentials, or generated bundles need to be committed.

See [the progress tracker](project-plan.md) for verification results and remaining
integration work.
