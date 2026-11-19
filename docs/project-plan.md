# ServerWatch project plan and progress

Last reviewed: 2026-11-19. Status is based on repository inspection, not a live
EC2 audit. This is the progress tracker; endpoint details remain in
[the API specification](api.md).

## Current position

**All four backend APIs are implemented. The next milestone is the native Ubuntu deployment for G.**

The project has a runnable FastAPI application factory, validated settings,
shared error handling, dependency manifests, and a passing foundation test suite.
Swagger/ReDoc and OpenAPI are available locally. The health GET route now
requires a numeric `server_id` and returns structured readiness; its database check
uses PostgreSQL `SELECT 1` when configured; the user verified Windows connectivity.
Server GET returns native host identity with reader authentication. Metrics GET/POST
now persist samples through SQLAlchemy with a versioned Alembic migration and
separate reader/collector credentials. A local collector now submits real host
measurements with a five-second sleep, and the API dashboard polls every five
seconds. Incident CRUD now uses reader GET and admin writes; Ubuntu systemd units provide continuous collection. Threshold alerts and Cron backups are outstanding. React live mode reads the three available APIs and explicitly marks
incidents unavailable. Real browser/Windows metrics verification remains pending.
The user reported 8/8 native monitoring checks passing on EC2. Reboot and
public browser verification remain pending.

| Workstream | Current status | Evidence |
| --- | --- | --- |
| Project scope and API design | Four API resources implemented | `README.md`, `docs/api.md` |
| Organization and security guidance | Documented | `docs/FOLDER_STRUCTURE.md`, `docs/SECRETS_MANAGEMENT.md` |
| Agent workflows | Instructions present | `AGENT.md`, `.agents/skills/` |
| Backend foundation and tests | Verified | `backend/app/main.py`, `backend/app/core/`, `backend/tests/`; verification below |
| Health API | Verified route/service behavior; user confirmed Windows database health | `backend/app/api/health.py`, schemas/services, and `backend/tests/test_health.py` |
| Server API | Implemented; native EC2/container verification pending | Server router/schema/service and tests; reader token authentication |
| Metrics and persistence | Implemented and tested with isolated PostgreSQL | Metrics model, Alembic upgrade, transaction, filtering, and persistence tests; both migrations present in the verified local incident database |
| Incident endpoints | Verified locally on Windows | CRUD, resolution/reopening, and deletion verified through FastAPI against local PostgreSQL; automated persistence/error tests also pass |
| React frontend | Live health/server/metrics integrated; browser check pending | 27 passing frontend tests, successful typecheck/build/format; no incident API calls |
| Infrastructure and CI/CD | Native monitoring setup implemented; EC2 run pending | Bash installer and verifier, API/collector systemd units, and isolated provisioning tests |
| Deployment and demo | Not verified | Host setup guides exist. The timed pair runbook and EC2 evidence are pending. |

The application language decisions are **Python for the backend/API** and
**React with TypeScript for the frontend**. The frontend is planned project work,
but is not recorded as a mandatory G/VG assessment requirement. Prioritize the
deployment requirements before dashboard polish.

## Scope and sources

- One monitored Ubuntu EC2 server, with health, metrics, server information, and
  incident CRUD APIs under `/api/v1`: [API contract](api.md).
- FastAPI/Pydantic, SQLAlchemy/Alembic, PostgreSQL, and Docker Compose:
  [architecture and conventions](../AGENT.md).
- Bash/Cron for host monitoring and backups; Nginx/Certbot for public HTTPS.
- Credential handling: [secrets management](SECRETS_MANAGEMENT.md).
- File placement: [folder structure](FOLDER_STRUCTURE.md).
- Frontend setup and data modes: [frontend development](frontend.md).

The [Swedish assignment brief](assignment-brief.md) defines G, VG, the optional
bonuses and the pair recording. Windows is a local development convenience.
The assessed deployment runs on EC2. The React dashboard is a project extension.

## Implementation milestones

Phase 1 is **Verified**; phases 2–5 and 7 are **In progress**. Phases 6 and 8
remain **Not started**. Phase 5 has native test scripts but no EC2 verification.
Health and server GET are implemented. Phase 2
still needs real host verification of identity and database connectivity. Complete
each milestone with observable evidence. Owners and deadlines are unassigned.

| Phase | Deliverables | Completion evidence | Status |
| --- | --- | --- | --- |
| 1. Local backend foundation (Python, FastAPI, pytest) | Python dependency manifest, application entry point, configuration, structured error handling, test setup, documented local startup | App starts locally; smoke tests pass; invalid configuration fails without exposing values. No required credentials exist at this stage | Verified |
| 2. Persistence and read endpoints (Python, PostgreSQL, Alembic) | PostgreSQL connection, SQLAlchemy models, Alembic migrations, health and server GET routes | Migrations apply to an isolated database; health reports dependency failure; server identity describes the host correctly | In progress |
| 3. Metrics and incidents (Python, FastAPI, pytest) | Auth/permissions, metrics GET/POST, full incident CRUD, pagination and validation | Unit and API contract tests cover the matrix in `api.md`; database integration tests prove persistence and rollback | In progress |
| 4. Monitoring and recovery (Bash, Cron, Python, PostgreSQL) | Host collector, Cron schedules, threshold detection, alert delivery, PostgreSQL/log backup and restore scripts | A collected sample is stored; a controlled breach produces an incident and alert without duplicate open incidents; isolated restore succeeds | In progress |
| 5. Native EC2 deployment — G (AWS EC2, Bash, systemd, Nginx) | Bootstrap via SCP, repository setup, independent student SSH access, native service, Nginx, scheduled operations | Rehearsed fresh-instance deployment; API/database connectivity, restart behavior, monitoring, and backups demonstrated | In progress |
| 6. Containers and HTTPS — VG (Docker, Docker Compose, DNS, Certbot) | API Dockerfile, separate API/PostgreSQL Compose services, persistent volume, domain, Certbot | Compose validation and health checks pass; records survive restart; HTTPS and renewal checks pass; native service stopped before port reuse | Not started |
| 7. Frontend (React, TypeScript) | React/TypeScript app, typed API client, health/metrics/server views, incident management | Type checking/build pass; UI handles loading, empty, validation, permission, and unavailable states; core flows work against the API | In progress |
| 8. Demo preparation (Documentation, Deployment, Presentation) | Deployment runbook, requirement checklist, timed rehearsal, evidence and speaking roles | Both students complete and explain a fresh-instance rehearsal within the 60-minute limit | Not started |

At the user’s request, frontend development has started before phases 2–3,
using the documented contract and clearly labeled demo data. Live integration
remains dependent on working endpoints and authentication. The deployment
requirements still apply as backend/infrastructure work continues. GitHub Actions
CI/CD remains optional; local verification is required regardless of CI.

### Tasks by topic

Each row is a task within the corresponding milestone. Topics identify the
language, tool, or work area involved and appear in parentheses beside each
task name. A task can involve several topics.
Tasks 1.1–1.3 and 7.1 are **Verified**. Tasks 7.2–7.3 are **In progress**, with
demo behavior and automated checks passing but live integration/browser review
pending. Tasks 5.2–5.4 are **In progress** with test scripts and a service template.
Task 2.2 is **In progress** with both routes implemented and host verification pending.
Database, authentication, metrics, incident CRUD, and local collection are now
implemented; see their individual status rows and dated verification below. Each task uses the completion
evidence for its parent milestone above.

| Task (topics) | Work to complete | Status |
| --- | --- | --- |
| 1.1 Backend setup (Python, FastAPI) | Add dependencies, application entry point, and local configuration. | Verified |
| 1.2 Errors and test foundation (Python, Pydantic, pytest) | Add structured error handling and test setup; verify startup and configuration failure paths. | Verified |
| 1.3 Local development guide (Documentation) | Document verified installation, startup, and test commands. | Verified |
| 2.1 Database connection and schema (Python, PostgreSQL, SQLAlchemy, Alembic) | Connectivity, metrics/incident models, pooled sessions, and both migrations implemented; Windows incident table access verified. | In progress |
| 2.2 Health and server endpoints (Python, FastAPI, Linux) | Implement health and server GET routes, including dependency failure and correct host identity. | In progress |
| 2.3 Persistence verification (Python, pytest, PostgreSQL) | Metrics migration, persistence, rollback, and filtering tested in private temporary PostgreSQL; Windows metrics run pending. | In progress |
| 3.1 Authentication and validation (Python, FastAPI, Pydantic, Security) | Reader/collector/admin roles and request validation implemented; private local admin credential verified in the Windows incident smoke test. | In progress |
| 3.2 Metrics endpoints (Python, FastAPI, PostgreSQL) | GET/POST, filtering, pagination, database uniqueness, persistence, and frontend reads implemented. | Verified locally |
| 3.3 Incident endpoints (Python, FastAPI, PostgreSQL) | Implement incident create, read, update, and delete behavior. | Verified locally, including Windows CRUD smoke check |
| 3.4 API and business logic tests (Python, pytest, PostgreSQL) | Metrics and incident API/PostgreSQL tests implemented; Windows incident CRUD verified, full Windows metrics flow pending. | In progress |
| 4.1 Host metrics collection (Python, Bash, Linux, HTTP) | Local Python loop and Ubuntu systemd installer/verifier implemented; native server/reboot verification and Cron evidence pending. | In progress |
| 4.2 Scheduled health checks (Linux, Monitoring) | Verify monitoring starts on boot and configure recurring threshold checks for G6. Cron is required for backups in G5. | In progress |
| 4.3 Incident detection and alerts (Python, Monitoring) | Detect threshold breaches, avoid duplicate open incidents, and deliver alerts through the selected channel. | Not started |
| 4.4 Backup and restore (Bash, PostgreSQL, Cron) | Script database/log backups, schedule them, and verify an isolated restore. | Not started |
| 5.1 EC2 and student access (AWS EC2, Linux, SSH) | Prepare the instance configuration and independent access for both students. | Not started |
| 5.2 Server bootstrap (Bash, SCP, Git, Linux) | Ubuntu installer prepares a cloned checkout with Python, PostgreSQL, and migrations. SCP and fresh instance verification remain pending. | In progress |
| 5.3 Native service and reverse proxy (systemd, Nginx, Linux) | Native verifier passed 8/8 on EC2, as reported by the user. Nginx setup and web verification scripts are implemented. Run the [public IP rehearsal](ec2-manual-setup.md#7-serve-the-dashboard-and-api-through-nginx-bash-react-fastapi) and capture browser evidence. | In progress |
| 5.4 Native deployment verification (Bash, Linux, Testing) | Localhost smoke verifier added; fresh-instance verification, restarts, scheduled monitoring, and backups remain pending. | In progress |
| 5.5 Define and verify environment access (Ubuntu, Bash, Linux users, groups, ACLs) | Define dev/prod ownership and role membership, provision accounts and inherited permissions, then check effective allowed and denied operations as each identity. See the [proposed access matrix](ubuntu-monitoring.md#planned-linux-users-groups-and-permissions). | Future task. No host changes applied. |
| 6.1 API image (Docker, Python) | Create the API Dockerfile and build a runnable image. | Not started |
| 6.2 Container services and storage (Docker Compose, PostgreSQL) | Configure separate API/database services, private networking, health checks, and persistent storage. | Not started |
| 6.3 Domain and TLS (DNS, Nginx, Certbot, HTTPS) | Configure the custom domain, certificate, redirects, and renewal. | Not started |
| 6.4 Container deployment verification (Docker Compose, Testing) | Validate configuration, health, and persistence; stop the native API before reusing its port. | Not started |
| 7.1 Frontend foundation (React, TypeScript) | Set up the frontend project and typed API client. | Verified |
| 7.2 Dashboard and incident management (React, TypeScript, CSS) | Build health, metrics, server, and incident views with the required UI states. | In progress |
| 7.3 Frontend verification (TypeScript, Frontend testing) | Run type checking/build and verify core UI flows against the API. | In progress |
| 8.1 Runbook and assessment checklist (Documentation) | Record deployment steps, requirement evidence, and speaking roles. | Not started |
| 8.2 Timed pair rehearsal (AWS EC2, Deployment, Presentation) | Rehearse from a fresh instance within 60 minutes, with both students explaining their work. | Not started |
| PR checks and optional VG4 delivery (Git, GitHub Actions, Docker) | [Human and agent workflow](github-actions-plan.md). Test PRs and pushes to main with backend, dashboard and Bash jobs. | Test-only workflow implemented locally. Hosted run and branch rules pending. Docker delivery deferred. |

Python tasks include unit tests and clear comments or multiline docstrings for
non-obvious behavior. Bash tasks include syntax checks and failure-path checks;
Docker tasks include build/configuration and runtime checks as applicable.
Keep task status and evidence alongside these rows when implementation begins.

## Assignment coverage tracker

The [assignment brief](assignment-brief.md) is the source for this tracker. Local
tests establish application behavior. The recorded pair deployment supplies the
evidence for the EC2 requirements.

| Requirement (topics) | Current evidence | Still needed for the assignment |
| --- | --- | --- |
| G1 Fresh instance (AWS EC2, networking) | No instance creation verified. | Create a free-tier-configured instance on camera with suitable AMI, security groups and Elastic IP. |
| G2 Pair access (SSH, Linux) | The EC2 guide covers an individual SSH connection. | Show both students logging into the same host from their own computers with independent keys. |
| G3 Bootstrap (Bash, SCP, Ubuntu) | Bash setup installs packages and configures services and permissions. The older smoke-test guide demonstrates SCP. | Include useful shell aliases, rehearse transferring and running the chosen bootstrap on a fresh instance, and explain account choices. |
| G4 Repository checkout (Git, Linux) | Home-directory clone documented. Full installer expects an existing user-owned checkout. | Perform the clone as the deployment user and show ownership and the order of steps. |
| G5 Backups (Bash, Cron, PostgreSQL) | Cron directory reserved. | Implement scheduled on-instance backups, show the files created and verify a database restore. |
| G6 Monitoring and alerts (Linux, Python, Discord or email) | Host collector samples every five seconds, with a systemd unit and verifier for fresh stored measurements. | Verify on EC2 and demonstrate a scheduled check sending a notification for a controlled threshold breach. |
| G7 Public API docs (systemd, FastAPI, HTTP) | Web installer opts into Swagger and OpenAPI on the existing loopback API. | Open public-IP `/docs` and `/openapi.json` from a browser on EC2 rehearsal. |
| G8 Reverse proxy (Nginx) | Site serves the static React build and proxies API requests. | Run the web installer and verifier on EC2 and confirm public HTTP routing. |
| G9 Database connection (FastAPI, PostgreSQL) | Local health and Windows incident CRUD verified against PostgreSQL. Migrations and persistence tested with disposable PostgreSQL. | Show the deployed API reading and writing through the instance's database. |
| VG1 Containers (Docker, Compose, PostgreSQL) | No project Dockerfile or Compose configuration. | Build and run API and database containers on EC2, demonstrate persistence and also show the native process manager. |
| VG2 Custom domain (DNS, HTTPS, Certbot) | No verified domain or TLS setup. | Point a domain at the instance, issue a certificate and demonstrate working HTTPS. |
| Optional VG3/VG4 (AWS RDS, GitHub Actions) | Neither bonus is implemented. | If selected, demonstrate the RDS alternative or automatic Docker image deployment to EC2. |
| Team and recording (Classroom, documentation, presentation) | Team membership and a timed rehearsal are unverified. | Accept the invitation, document the pair, rehearse from scratch, record within 60 minutes, check playback and the link, then stop the instances. |

## Decisions to settle

- Record the two team members, course deadline and division of demo work when confirmed.
- Local collection uses a five-second sleep. Define the production collection
  schedule, incident thresholds, automatic resolution policy, retention, and
  notification channel.
- Choose how a containerized API obtains the monitored host's identity and
  health without reporting only its own container metadata.
- Identify domain/DNS ownership, backup storage location, and recovery procedure.
  Local backups alone do not protect against losing the instance.

## Immediate next task

Verify the first [CI workflow run](github-actions-plan.md) when the branch is published and a PR targets main (Git, GitHub Actions).
Prepare and rehearse the G deployment on a fresh Ubuntu instance (Bash, SCP,
Git, SSH, systemd). Verify both logins, the home-directory clone, PostgreSQL and
a fresh host metric. Then add Nginx and configure public Swagger and OpenAPI for
the demonstration (Nginx, FastAPI). Schedule backups and demonstrate an alert
before moving on to Compose and HTTPS. Windows and React work can proceed as
local conveniences outside the grading path.

## API error feedback (FastAPI, React, pytest)

Health and server lookups distinguish out-of-range, non-integer and repeated
IDs. Metric and incident requests report input rules, and the dashboard shows
structured client errors. The API preserves machine codes and the health 503
report. The [API contract](api.md) makes a safe explanation mandatory for every
handled error. The audit covered all nine operations, routing, auth, schema and
storage failures, and the dashboard's public error display.

The backend and automation suite passed 384 cases. The final 27-case handler
run includes one additional response-schema regression. All 32 frontend tests,
type checking, build, formatting, backend lint and Bash syntax checks passed
locally. The CI workflow has been checked locally. A GitHub-hosted run is pending.

## Repository maintenance (Python, pytest, Git)

The four routers share request validation in `backend/app/reusable.py`. Metric
and incident schemas also share UTC timestamp validation. Direct helper tests
live in `backend/tests/test_reusable.py`. Repository skills cover extracting
duplicate Python behavior and keeping placeholders only where Git needs them.
All 367 backend and automation tests passed after the refactor, including 17
new helper cases. Ruff lint and format checks passed for the backend app and tests.

## Verified foundation evidence (2026-11-16)

- Runtime: Python 3.14.4 in the local `.venv`; direct dependencies pinned in
  `backend/requirements.txt` and `backend/requirements-dev.txt`.
- `python -m pytest backend/tests -q`: **20 passed**. Covers app/docs startup,
  production documentation disabling, settings validation, shared HTTP errors,
  malformed JSON, validation, and sanitized failures. Test routes are not
  registered in the production application.
- `python -m ruff check backend` and `python -m ruff format --check backend`:
  passed.
- `python -m pip check`: no broken requirements.
- Uvicorn factory startup on `127.0.0.1:8000` succeeded; an HTTP request to
  `/openapi.json` returned `200` with an empty business-route list. The temporary
  verification server was stopped afterward.
- Local secret/environment paths and `.venv/` are excluded by `.gitignore`;
  `.env.example` contains non-secret configuration only.

The restricted agent sandbox blocked socket binding and stalled the test client;
HTTP tests and the startup check passed outside that sandbox. No PostgreSQL,
full business endpoints, authentication, Docker, or AWS checks have been
performed. See [the README](../README.md#local-backend-setup-python-fastapi)
for local setup and verification commands.

## Frontend progress and evidence (2026-11-16)

- User-selected priority: defer backend implementation and develop the frontend.
  No backend application files were changed in this task.
- React/TypeScript/Vite foundation, modular views/components, typed API client,
  response validation, and a committed npm lockfile are present under `frontend/`.
- Overview, metrics, server details, and incident management work with explicitly
  labeled sample data. Demo incidents support create/read/update/delete,
  resolution/reopening, search, status filtering, and deletion confirmation.
- API mode uses bearer authentication in memory and shows failures without demo
  fallback. Readiness 503 responses remain unhealthy; failed writes retain the
  editor and its input. Requests use the documented paths/methods.
- `npm run typecheck`: passed.
- `npm test`: **21 passed** across API client, demo lifecycle, and rendered UI
  tests. Responses and tokens are dummy values; this is not live integration.
- `npm run build`: passed and emitted the static bundle to ignored
  `frontend/dist/`.
- `npm run format:check`: passed.
- Vite started on `127.0.0.1:5173`; an HTTP request returned the app entry page
  with `200`. This verifies serving, not browser rendering.
- Remaining: real browser visual/responsive/keyboard checks, real backend
  integration, server-side pagination beyond loaded records, and production
  frontend/reverse proxy deployment. Phase 7 is not fully verified.

Use [the frontend guide](frontend.md) for startup, test commands, sample-data
limitations, and the future connection workflow.

## Health API evidence (2026-11-16)

- Implemented only `GET /api/v1/health`, with separate router, response schemas,
  and a service containing injectable asynchronous probes and a UTC clock.
- Default behavior: `503`, `status: unhealthy`, `server: up`, `database: down`.
  No database configuration or credential is required for this first endpoint.
  Local API availability is not proof of complete host/EC2 health.
- Verified injected successful probes return `200`; failures/exceptions/timeouts
  return `503` and remain sanitized. Timeout tests verify probe cancellation.
- Verified no authentication is required, only GET is accepted, `Allow: GET` is
  preserved, input bodies/query parameters were rejected (updated below), timestamps are UTC,
  and health responses disable caching.
- `python -m pytest backend/tests -q`: **36 passed**, including the foundation
  regression tests and new health coverage. No live database or EC2 calls.
- `python -m ruff check backend` and formatting checks passed.
- Real database connectivity, persistence, and host/container metadata remain
  unverified and unimplemented. Phase 2 is still in progress.

## Health server lookup update (2026-11-17)

- Health now requires `server_id`; the single registered local server has ID `1`.
- Invalid, negative, zero, malformed, or duplicate IDs return `400`;
  valid unregistered IDs return `404`; missing input returns `422`.
- Responses identify the server. Failed, exceptional, or timed-out probes return
  structured `503`; unexpected application bugs return sanitized `500`.
- The frontend client supplies `server_id=1`. Remote monitoring and a real
  database check remain pending; default readiness remains `503`.
- Verification: **53 backend tests passed**; Ruff lint and formatting checks
  passed. Frontend type checking and Prettier checks passed. Frontend tests
  could not start because the local installation lacks
  `@rollup/rollup-linux-x64-gnu`; no new frontend test pass is claimed.
- Documentation links resolve; scoped whitespace checks passed with CRLF
  recognized as the existing Markdown line ending.

Readability update: health ID validation now uses `int()` with `try`/`except`
and a simple minimum check. The regex and application-specific maximum were
removed. Extra query parameters and request bodies are checked separately.
Verification: **55 backend tests passed**; Ruff lint and formatting checks passed.

## Health response speed verification (2026-11-17)

- Reduced the default per-probe timeout from one second to 150 ms. Probes run
  concurrently; slow probes are cancelled and marked down, returning `503`.
- Added local latency checks: healthy and default-unhealthy responses have p95
  below 200 ms across 20 warmed-up requests each. Server-only, database-only,
  and combined slow probes returned `503` within 200 ms using the default timeout.
- **60 backend tests passed**; Ruff lint and formatting passed. Documentation
  links resolve and scoped whitespace checks passed with existing CRLF endings.
- This verifies local behavior with injected probes. Deployment/network latency
  and real database performance remain unverified; 200 ms is a target, not a
  hard deadline under every load or network condition.

## Server API evidence (2026-11-17)

- Implemented GET-only `/api/v1/server` with a router, response schema, native
  metadata service, and reader bearer authentication. Numeric server ID/name
  are configured in settings; health uses the same ID. No creation API added.
- Client failures: missing/invalid credentials `401`, unsupported inputs `422`,
  unsupported methods `405`. Missing/unreadable/incomplete host metadata and
  detected container metadata return `503`; unexpected failures return sanitized
  `500`. Host reads run in a worker thread rather than blocking the event loop.
- Reader credentials support an environment variable or protected mounted file
  with file precedence. Tests use dummy tokens and temporary files. No real
  credential was created or read. Ignore rules cover `.env` and secret files.
- **97 backend tests passed**; Ruff lint/format checks passed. Tests include
  service metadata extraction and HTTP contract/error cases, plus configured ID
  consistency with health. Documentation links and scoped whitespace checks pass.
- Frontend types/demo/response validation now use numeric server IDs. Type checks
  and Prettier pass. Frontend tests could not start because the local install
  lacks `@rollup/rollup-linux-x64-gnu`; no new frontend test pass is claimed.
- Native EC2 verification, an explicit container host metadata source, full
  frontend integration, database persistence, and collector/admin roles remain
  pending. Phase 2 and task 2.2 remain in progress.

## Optional server selection update (2026-11-17)

- `/api/v1/server` still returns the configured server when no ID is supplied.
  Optional `?server_id=1` explicitly selects a registered server. Only the local
  configured ID is registered; remote discovery/registration is not implemented.
- Shared readable ID validation serves health and server information: invalid,
  zero, negative, or repeated IDs return `400`. Unregistered IDs return `404`
  before host metadata is read. Known-server metadata failures remain `503`.
- **110 backend tests passed**, including optional selection, invalid/duplicate
  IDs, missing resources, and selected-server failure cases. Ruff lint and
  formatting passed; documentation links and scoped whitespace checks passed.

## Native EC2 testing scripts (2026-11-17)

- Added Ubuntu setup under `infrastructure/bootstrap/`, a localhost-only
  `serverwatch-ec2-test.service` template, and a read-only API/setup verifier under
  `scripts/verification/`. Usage and scope: [EC2 testing guide](ec2-testing.md).
- Setup installs runtime prerequisites into an existing checkout, creates a
  private reader token outside Git, and enables/restarts the dedicated service.
  It does not provision EC2, clone/update Git, or configure the full deployment.
- Verification prints PASS/FAIL/WARN and a summary; expected database-down health
  is a warning. Failed checks return a nonzero exit code. Authenticated HTTP
  credentials go through stdin, not process arguments or printed output.
- Bash syntax and help checks passed. Three simulated verification tests passed,
  covering working setup, server HTTP failure, and a missing token without leaks.
  Rendered systemd unit verification returned exit 0 (sandbox socket warnings).
- ShellCheck is unavailable locally. Package installation and actual systemd
  startup on native EC2 remain unverified; no AWS resources were accessed.

## Maintaining progress

After a milestone or material scope change:

1. Update the review date and relevant status rows.
2. Record evidence as file links, executed commands/results, and verification
   dates. Mark unavailable checks as unverified.
3. Keep endpoint details in `api.md`; synchronize README and `AGENT.md` references
   using the repository's documentation synchronization skill.

Use `Not started`, `In progress`, `Blocked` (with a concrete reason), or `Verified`
for future status updates. A milestone becomes verified only when its completion
checks have actually passed. Local documentation changes do not authorize cloud
provisioning, deployment, or credential operations.

## PostgreSQL connectivity (Python, Psycopg) — 2026-11-18

- Added optional private database settings and password-file precedence.
- Health now executes asynchronous `SELECT 1` against configured PostgreSQL.
  Missing configuration, failed connections, and timeouts remain unhealthy.
- Added Windows setup instructions in [local PostgreSQL](local-postgresql.md).
- Verified 118 backend tests, Ruff lint/format, and dependency consistency.
  Tests use fake database connections and dummy credentials.
- Live Windows PostgreSQL connectivity, tables, migrations, persistence APIs,
  pooling, and EC2 database deployment remain unverified or unimplemented.

## Metrics and frontend integration — 2026-11-18

- Metrics GET/POST (Python, FastAPI): strict host sample validation, UTC times,
  reader/collector role separation, duplicate timestamps as 409, safe 503 storage
  failures, filtering, pagination, and unsupported-input checks.
- Storage (Python, PostgreSQL, SQLAlchemy, Alembic): transactional metric model,
  server/time uniqueness, bounded connection pool, explicit reviewed upgrade,
  and consistent count/page snapshots. No automatic schema changes at startup.
- Frontend (React, TypeScript): reader connection loads server, matching public
  health, and metrics GET; real empty states; incidents explicitly unavailable.
  Demo data and credentials remain separate from live API records.
- Verification (Python, pytest): **192 passed**, including a private disposable
  PostgreSQL cluster, migration/schema consistency, duplicate rollback, persisted
  records across fresh connections, time filters, boundaries, missing schema,
  and an offline migration-command preview. Ruff lint/format and pip check passed.
- Verification (React, TypeScript): **27 tests passed**, typecheck, production
  build, and formatting passed. No browser visual verification was performed.
- User action (Windows, PostgreSQL): install updated requirements, run the upgrade
  from the local PostgreSQL guide, configure different reader/collector tokens,
  restart FastAPI, then verify a submitted sample in the dashboard.
- Remaining (Bash, Python, FastAPI): automatic collection, application-specific
  metrics, incidents/admin credentials, deployment, and Windows browser end-to-end
  verification are not part of this completed metrics implementation.

## Local stack launcher (Bash, PowerShell, Python, Windows) — 2026-11-18

- Added one Bash entry point for the existing Windows PostgreSQL service,
  Windows FastAPI, and Windows React/Vite, usable from Git Bash or WSL interop.
- Added checks for dependencies, private local configuration, free ports, metrics
  schema access, and app HTTP startup. Existing apps are never terminated to free
  ports; owned app processes are cleaned up, while PostgreSQL remains running.
- No dependency installation, migrations, credential generation, data writes,
  collector, or automatic dashboard refresh is performed by the launcher.
- Verification: Bash syntax/help, Ruff lint/format, and **17 passing automation
  tests** (14 launcher/configuration cases plus 3 existing EC2 verifier cases).
  Dispatch tests cover Git Bash/WSL, paths with spaces, and nonzero exit status.
  Native Windows service startup and Ctrl+C cleanup still require a Windows smoke test. See [local development](local-development.md).

## Five-second local monitoring (Python, React, TypeScript) — 2026-11-18

- Added `scripts/monitoring/collect_local.py`: actual psutil CPU/memory/home-volume
  disk/uptime sample, authenticated local POST, and `time.sleep(5)` in a simple
  while loop. Three-second HTTP timeout; failures are skipped and retried with a
  fresh sample after sleeping. No queues, services, or production scheduler added.
- The Windows local launcher starts/stops the collector with the apps and checks
  psutil plus distinct reader/collector configuration before starting services.
- Connected React mode polls every five seconds, skips overlapping slow polls,
  recovers from errors, cancels updates after cleanup, and shows the latest
  measurement time. Demo mode still makes no automatic requests.
- Verification: 24 automation tests passed (15 launcher, 6 collector, 3 existing
  EC2 verifier); 29 frontend tests passed. Python lint/format, dependency checks,
  Bash syntax, frontend typecheck, build, and formatting passed. Frontend checks
  used a temporary Linux copy; Windows node_modules was preserved.
- User action: install updated Python requirements (psutil), configure the private
  collector token, restart the launcher, and connect the dashboard with the reader
  token. Windows process startup/browser verification still requires a local run.
- Remaining: durable delivery, EC2/Cron monitoring, alerts, incidents, and backups.


## Incident CRUD (Python, FastAPI, PostgreSQL, Security) — 2026-11-18

- Added POST/list GET/detail GET/PATCH/DELETE under `/api/v1/incidents` with
  strict text/enum/aware-time validation, UUID validation, unsupported-input
  rejection, filters, pagination, generated fields, and Location/no-store headers.
- Incident writes require a separate optional admin token with environment/file
  support; GET remains reader-only. All configured role tokens must differ.
  Missing admin configuration fails closed for writes without disabling metrics.
- Added migration `0002_incidents`, transactions, server scoping, update/delete
  row locks, and resolution/reopening timestamp behavior. PostgreSQL-returned
  timestamps are normalized to UTC. Existing metrics migration remains unchanged.
- Verification: **299 backend tests passed**, including isolated PostgreSQL CRUD,
  rollback, persistence, status transitions, missing-table failures, and a repeated
  upgrade of an existing metrics-only schema preserving its measurement.
  The existing **24 launcher/collector/EC2 verification tests** also passed.
  Ruff lint/format and dependency checks passed. No real local database or secret files were read
  or changed, and no AWS resources were accessed.
- Local action: run the documented upgrade, configure the separate admin token
  privately, restart FastAPI, and verify CRUD in Swagger. See
  [incident setup](local-postgresql.md#enable-incident-storage-python-postgresql).
- Live React incident integration, automatic detection, alerts, and production
  deployment remain pending. The existing dashboard still shows incidents as
  unavailable in connected mode; demo incidents remain separate.


## Windows incident verification (Python, FastAPI, PostgreSQL) — 2026-11-18

- User configured the separate admin token privately. Verification loaded local
  credentials without displaying their values and used only Windows localhost.
- Started a temporary Windows FastAPI process against the existing local
  PostgreSQL database. Incident routes and reader list access returned 200.
- Created one uniquely named temporary incident (201), read it (200), resolved
  it with a resolution timestamp (200), and reopened it with that timestamp
  cleared (200). Deleted only that temporary incident (204); a subsequent GET
  returned 404. Existing records were not edited or deleted.
- Stopped the API process created for this check; PostgreSQL remained running.
  The temporary verification script was removed. No credentials, configuration,
  migrations, AWS resources, or production services were changed.
- Live Windows incident CRUD is verified. React incident integration, full local
  collector/dashboard verification, automatic detection, and deployment remain
  separate outstanding tasks.


## Ubuntu monitoring automation (Bash, Python, PostgreSQL, systemd) — 2026-11-19

- Added native Ubuntu setup for an existing checkout: runtime packages, dedicated
  local database/role, private generated credentials, migrations, API and collector
  services. The existing five-second Python collector measures the Ubuntu host.
- Added read-only verification for services, private configuration, loopback
  listeners, migration head, API/host identity, and a fresh persisted metric.
- Setup reruns preserve credentials and records; conflicting managed deployments
  or incompatible configuration fail safely. See [Ubuntu monitoring](ubuntu-monitoring.md).
- All 350 backend and automation tests passed, including disposable PostgreSQL
  provisioning, SCRAM login, rerun preservation, and the verifier’s fresh
  measurement checks. Bash syntax, Python lint/format, and rendered systemd
  unit validation also passed.
- Package installation, service startup, and a reboot on a fresh Ubuntu/EC2
  host remain to be verified.
- React/public access, Nginx/HTTPS, Cron assessment evidence, backups/restore,
  automatic incident detection, notifications, and durable collection remain pending.
