# Frontend development (React, TypeScript, Vite)

The frontend is a local React application under `frontend/`. Live mode supports
reader-authenticated server information and stored metrics, plus public health
with the real PostgreSQL readiness check. Incidents are labeled unavailable
instead of blocking the available views or substituting demo data.

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
| Incidents | Demo-only search, filters, CRUD, and resolution/reopening; live mode explicitly unavailable |

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

Run FastAPI on `127.0.0.1:8000` and Vite on `127.0.0.1:5173`.
Configure a private `SERVERWATCH_READER_TOKEN` in the backend environment before
starting FastAPI (see [backend setup](../README.md#local-backend-setup-python-fastapi)).
This token is separate from your PostgreSQL password.

Select **Connect API** and supply that reader bearer token. The token is kept in
memory, cleared on reload or return to demo mode, and never put in local storage or a
`VITE_*` build variable. Do not put real tokens in tracked files.

The client in `frontend/src/services/api.ts` follows [the API contract](api.md):

- Reads authenticated `/server`, then public `/health?server_id=<id>` using
  the returned server ID. No bearer token is sent with the health request.
- Incidents are explicitly unavailable in API mode until their backend is
  implemented. No incident read requests are sent, counts display unavailable,
  and incident creation/editing is disabled. Demo incident editing remains local.
- Reads the latest 100 stored measurements from authenticated
  `/metrics?limit=100`. Cards, charts, history, and reported uptime use those
  records. Empty results display no measurements rather than sample values.
  A failed metrics request is an error, not a successful empty collection.
- The dashboard uses the reader token only. Metric POST requests belong to a
  separately authorized collector; collector credentials never belong in the UI.
  Apply the backend migration before connecting; see
  [local PostgreSQL setup](local-postgresql.md).
- Uses same-origin `/api/v1` paths. The Vite development proxy forwards `/api`
  to `http://127.0.0.1:8000`, avoiding a backend CORS change.
- Applies a request timeout, validates response shapes before rendering, and
  shows safe error messages for connection, authentication, permission,
  validation, and server failures. For a structured API 4xx error the dashboard
  displays the public explanation and any field-specific reasons. Proxy errors
  and unexpected server failures use a local fallback. A structured unhealthy health response with
  HTTP 503 is displayed as unhealthy.
- Demo incident search/status filters and metric table pagination apply to
  loaded records; the API workspace loads at most the latest 100 measurements.
  Fetching further server-side pages is future work.
- Fetches on connection or explicit refresh, then polls every five seconds in
  API mode. Slow polls do not overlap. Polling stops on unmount, reconnect, or
  return to demo mode. Failures show an error and a later successful poll recovers.
  Background polling does not clear the dashboard into a loading screen.
- Displays the latest measurement timestamp so an unchanged old record is visible
  as old data. Actual recording is handled by the local collector, not the browser.

API mode never silently substitutes demo data. Server, health, and metrics
requests must succeed and match their response contracts; failures display an
error with retry and return-to-demo actions. Unimplemented capabilities are represented
explicitly as unavailable, not as successful empty collections. A valid empty
metrics response means no measurements have been recorded. Refresh fetches
updated data; the browser never POSTs host measurements. The
[local launcher](local-development.md) runs a separate five-second Python collector.

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
paths and headers, HTTP failures, response validation, configured server IDs,
real metric refresh, empty metrics, unavailable incidents, and resolution timestamps.
Tests use dummy tokens and simulated responses, with no live server or database.
Native dialog methods are stubbed in jsdom, so these tests do not prove browser
focus trapping or visual layout.

The production build is emitted to ignored `frontend/dist/`. Google Fonts is
used for typography with system font fallbacks if unavailable. No screenshots,
assets, credentials, or generated bundles need to be committed.

See [the progress tracker](project-plan.md) for verification results and remaining
integration work.
