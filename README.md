# ServerWatch

ServerWatch is a server monitoring and incident management platform for an MLOps
course assignment. It is intended to monitor one Ubuntu server on AWS EC2,
store resource measurements, and expose an API for inspecting server health,
server information, and operational incidents.

The project aims to meet the course's G/VG deployment requirements while keeping
the implementation understandable, maintainable, and suitable for a portfolio.

## Current status

**All four APIs are implemented. The next milestone is a fresh Ubuntu EC2
deployment that continues collecting measurements after reboot.**

| Area | What works today |
| --- | --- |
| API and storage (Python, PostgreSQL) | Health checks the API process and its database connection. Server information comes from the host. Alembic migrations create the metrics and incidents tables. Incident CRUD was verified against local Windows PostgreSQL. |
| Dashboard (React, TypeScript) | Live mode reads health, server details, metrics, and incidents. Connect with the optional admin token over HTTPS or localhost to save incident plans and reports. Demo mode can rehearse the same workflow. |
| Ubuntu setup (Bash, systemd) | The installer configures PostgreSQL and enables API and collector services. The user reported 8/8 checks passing on EC2. Reboot and public web access still need verification. |
| CI (GitHub Actions) | Pull requests targeting `main` and pushes to `main` run Python tests with disposable PostgreSQL, dashboard checks, and Bash syntax checks. [Passing run on main at `3285a97`](https://github.com/EmirU116/server-api/actions/runs/44458684832) |

The Nginx installer serves the dashboard, API and Swagger over HTTP. Public
browser verification on EC2, scheduled monitoring with alerts, and Cron
backups with a restore check remain. The VG work adds
Docker Compose and HTTPS on a custom domain. [Project plan and assignment coverage](docs/project-plan.md)

## Start the local stack (Bash, Windows)

First prepare Windows PostgreSQL, the private `.env`, database migrations, and
Python and frontend dependencies. [Database setup](docs/local-postgresql.md) · [Launcher prerequisites](docs/local-development.md)

To start monitoring, stop any manually started API/frontend instances. From the project
root in Git Bash or WSL:

```bash
bash scripts/setup/start_local.sh
```

The launcher starts/reuses Windows PostgreSQL, checks database/schema access,
and starts Windows FastAPI, React, and the local measurement loop. Open
<http://127.0.0.1:5173> and connect with your reader token. The live dashboard
refreshes every five seconds. Watch the latest measurement timestamp to confirm
new samples arrive even when disk usage stays steady. Ctrl+C stops the apps and
collector and leaves PostgreSQL running.
See [local launcher setup and troubleshooting](docs/local-development.md).
Install updated Python requirements first (the collector uses `psutil`) and
configure separate reader/collector tokens privately in `.env`.

## Deploy to Ubuntu EC2 (Bash, Nginx, systemd)

On EC2, install Git and clone the repository into your SSH user's home directory.
Enter the checkout and replace
`PUBLIC_IP` with the instance's public IPv4 address.

```bash
bash setup.sh PUBLIC_IP
bash verify.sh PUBLIC_IP
```

Setup installs the native packages and FastAPI dependencies, applies migrations,
runs FastAPI and the collector under systemd, and publishes React and Swagger
through Nginx. It prepares Node.js/npm for the frontend build and installs and
starts Docker Engine with Compose for the VG1 deployment. It also schedules
daily native PostgreSQL and service log backups with Cron.
It runs verification automatically. Use the second command for later checks.
Open `http://PUBLIC_IP/` and `http://PUBLIC_IP/docs` from your computer. Use
HTTPS for live dashboard credentials.

Follow the [EC2 guide](docs/ec2-manual-setup.md) for package prerequisites, SCP,
security groups, public browser checks, and the assignment recording.

### Start Compose on EC2

From `~/serverwatch` on EC2, run these as the trusted Docker operator:

```bash
bash scripts/deployment/compose_host.sh start
bash scripts/deployment/compose_host.sh collect
```

`start` creates the default configuration when needed and starts Compose.
`collect` records real host metrics in the Compose database until you press
Ctrl+C. The [Compose guide](docs/docker-deployment.md) covers Docker access,
opening the live dashboard, and demonstrating database persistence.

### Request a project review

Type `code-review` in Codex to review the project, or add a scope such as
`code-review deployment`. You can also invoke the [review skill](.agents/skills/code-review/SKILL.md)
as `$code-review`.

## Local backend setup (Python, FastAPI)

Use Python 3.11 or newer. Run these commands from the repository root on
Linux/WSL:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
python -m uvicorn app.main:create_app --factory --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Open [Swagger UI](http://127.0.0.1:8000/docs),
[ReDoc](http://127.0.0.1:8000/redoc), or
[OpenAPI JSON](http://127.0.0.1:8000/openapi.json).
The route list includes `GET /api/v1/health`. Open
<http://127.0.0.1:8000/api/v1/health?server_id=1> to inspect readiness. Its default `503`
is expected until PostgreSQL is configured; it is not a startup crash.
A `404` at `/` is expected.
Use `--reload` for local development only. Stop the server with `Ctrl+C`.

The health response includes numeric `server_id`, UTC `checked_at`, `status`,
and `checks` for the server and database. It requires no token and supports GET
only. Supply the required `server_id=1` query parameter for the registered local
server. Invalid IDs (including negative numbers and zero) return `400`, unknown
positive IDs return `404`, and an omitted ID returns `422`. Bodies and unknown
query parameters return `422`. Probes run concurrently with a 150 ms timeout
each; exceptions become `down` without exposing their messages. At this stage,
`server: up` means the local API process is responding, not that a remote EC2
host or all operating-system resources have been verified. The database probe
executes an asynchronous PostgreSQL query when credentials are configured.
Without credentials it returns `down`. Health verifies connectivity, not schema
version; apply the metrics migration separately before using metrics endpoints.

Health requests are public. A healthy response requires a successful PostgreSQL
probe. Use the appropriate role's bearer token for protected requests. Readers
retrieve data, collectors submit metrics, and admins create, update, and delete
incidents. Configure distinct tokens and send the relevant one in the
`Authorization: Bearer <token>` header. To load a private `.env` file, start
Uvicorn with `--env-file .env`.

`GET /api/v1/server` returns the configured server by default. Optionally use
`GET /api/v1/server?server_id=1` to select it explicitly. Invalid, zero, negative,
or repeated IDs return `400`; unregistered IDs return `404`. Request bodies and
unknown query parameters return `422`. Native host metadata
includes numeric ID, display name, hostname, OS type/name/version, and architecture.
Common container environments return `503` until a host metadata source is added;
WSL describes its Linux environment. See the [server API contract](docs/api.md#server-api)
for errors and the testing strategy.

Settings come from
environment variables:

| Variable | Default | Allowed values |
| --- | --- | --- |
| `SERVERWATCH_APP_NAME` | `ServerWatch` | Nonblank name, at most 100 characters |
| `SERVERWATCH_ENVIRONMENT` | `development` | `development`, `test`, `production` |
| `SERVERWATCH_EXPOSE_API_DOCS` | `false` | Set to `true` to enable Swagger and OpenAPI in production for the assignment |
| `SERVERWATCH_SERVER_ID` | `1` | Positive integer; shared by health and server |
| `SERVERWATCH_SERVER_NAME` | `ServerWatch server` | Nonblank display name, at most 200 characters |
| `SERVERWATCH_READER_TOKEN` | Unset | Private reader bearer token without whitespace |
| `SERVERWATCH_READER_TOKEN_FILE` | Unset | Protected token file; takes precedence over token environment value |
| `SERVERWATCH_COLLECTOR_TOKEN` | Unset | Private metric-write token; must differ from reader token |
| `SERVERWATCH_COLLECTOR_TOKEN_FILE` | Unset | Protected collector token file; takes precedence |
| `SERVERWATCH_ADMIN_TOKEN` | Unset | Private incident-write token, distinct from the reader and collector tokens |
| `SERVERWATCH_ADMIN_TOKEN_FILE` | Unset | Protected admin token file taking precedence over the environment value |
| `SERVERWATCH_DATABASE_HOST` / `SERVERWATCH_DATABASE_PORT` | `localhost` / `5432` | PostgreSQL address; port 1–65535 |
| `SERVERWATCH_DATABASE_NAME` / `SERVERWATCH_DATABASE_USER` | `serverwatch` / `serverwatch_app` | Nonblank database and login names |
| `SERVERWATCH_DATABASE_PASSWORD` | Unset | Private database password |
| `SERVERWATCH_DATABASE_PASSWORD_FILE` | Unset | Protected password file; takes precedence |

Invalid settings and invalid configured reader credentials prevent startup with a
sanitized error. Without a configured token, health remains available while server
information fails closed. Production mode disables Swagger, ReDoc, and OpenAPI
by default. The Nginx installer sets `SERVERWATCH_EXPOSE_API_DOCS=true` to enable
Swagger and OpenAPI for the assignment.
It does not turn this foundation into a complete production deployment.

For optional local overrides, copy `.env.example` to an ignored `.env` and load
it explicitly:

```bash
cp -n .env.example .env
python -m uvicorn app.main:create_app --factory --app-dir backend --env-file .env --reload --host 127.0.0.1 --port 8000
```

Only copy the template when creating a new local configuration; preserve any
existing `.env`. Never commit real credentials. Tests do not load dotenv files.

Run checks from the repository root with the virtual environment active:

```bash
python -m pytest backend/tests tests -q -ra
python -m ruff check backend/app backend/tests
python -m ruff format --check backend/app backend/tests
python -m pip check
```

Tests cover all four APIs, including validation, role checks, and database
failures. PostgreSQL integration tests exercise migrations, metric persistence,
and incident CRUD using disposable databases. Run pytest as a non-root user
with PostgreSQL server tools installed to exercise those tests. The root `tests/`
directory covers the launcher, collector, and deployment scripts. [CI workflow](.github/workflows/ci.yml)

## Local frontend setup (React, TypeScript)

Use Node.js 22.12+ on the Node 22 release line (or a newer supported release):

```bash
cd frontend
npm ci --include=optional
npm run dev
```

Open <http://127.0.0.1:5173>. The frontend starts in a clearly labeled demo
workspace with sample server data. It includes overview, metrics, server details,
and incident management. Demo incident edits reset on page reload or a data-source
switch. No backend is needed for demo mode.

Run `npm run typecheck`, `npm test`, `npm run build`, and
`npm run format:check` inside `frontend/` to verify it. See the
[frontend guide](docs/frontend.md) for the API connection workflow, file ownership,
data limitations, and test scope. Live mode requires the metrics migration and
a reader token. See [database and metrics setup](docs/local-postgresql.md#enable-metrics-storage-python-postgresql-alembic).

## API scope

All routes use the `/api/v1` prefix and target a single monitored server.

| API | Methods and paths | Responsibility |
| --- | --- | --- |
| Health | `GET /health?server_id=1` | Report server and required dependency health. |
| Metrics | `GET /metrics`, `POST /metrics` | Read stored statistics and accept CPU, memory, disk, and uptime samples. |
| Server | `GET /server` | Return the server name, hostname, operating system, and architecture. |
| Incidents | `POST /incidents`, `GET /incidents`, `GET /incidents/{incident_id}`, `PATCH /incidents/{incident_id}`, `DELETE /incidents/{incident_id}` | Create, list, read, update, and delete incident records. |

The [API specification](docs/api.md) defines payloads, validation, authentication,
permissions, pagination, error responses, and required tests. Health is public;
the remaining endpoints require authentication under the implemented API contract.
Automatic threshold detection and alert delivery are broader project goals,
separate from the initial incident CRUD contract.

## How measurements reach the dashboard

```text
Host collector  --> POST /api/v1/metrics --> FastAPI --> PostgreSQL
React dashboard --> GET  /api/v1/metrics --> FastAPI --> PostgreSQL
```

The collector measures CPU, memory, disk usage, and uptime on the machine where
it runs. On Windows the local launcher starts it. On native Ubuntu, systemd runs
the collector and FastAPI as services. In both setups the collector writes
samples with its collector token and the dashboard reads them with a reader token.
[Ubuntu monitoring guide](docs/ubuntu-monitoring.md)

## Assignment and demonstration

The [Swedish assignment brief](docs/assignment-brief.md) sets the following requirements.

- **G:** provision a new EC2 instance, provide independent SSH access for both
  students, transfer and run a Bash bootstrap script, clone the repository,
  connect FastAPI to PostgreSQL, demonstrate a native service using systemd or
  supervisor, configure Nginx, and schedule backups, monitoring, and alerts.
- **VG:** run FastAPI and PostgreSQL in separate Docker Compose services and
  provide a custom domain with HTTPS using Certbot.
- **Recorded pair demo:** a maximum of 60 minutes, with the EC2 instance created
  from scratch during recording. Both students must explain their work.

The [coverage tracker](docs/project-plan.md#assignment-coverage-tracker) lists the evidence and remaining work for each criterion. Automated Docker deployment is a bonus. The frontend is an optional project extension.

## Repository layout

```text
backend/
  app/main.py          FastAPI application factory
  app/core/            Runtime settings and shared error handling
  app/api/             Health, server, metrics, and incident CRUD routers
  app/models/          Metrics and incident database models
  app/schemas/         API request and response models
  app/services/        Readiness, host identity, metrics, and incident operations
  alembic/             Versioned metrics and incidents migrations
  tests/               Unit, API, and PostgreSQL integration tests
  requirements.txt     Runtime dependencies
  requirements-dev.txt Test and lint dependencies
  pyproject.toml       pytest and Ruff configuration
frontend/              React/TypeScript dashboard, API client, and frontend tests
infrastructure/        Ubuntu bootstrap scripts and systemd services
scripts/               Local launcher, host collector, and deployment verification
tests/                 Automation tests for scripts and host setup
.github/workflows/     Test-only backend, dashboard and Bash CI
.agents/skills/        Repository agent workflows
docs/                  Specifications and project guides
AGENT.md               Agent instructions and project constraints
```

See the folder ownership table in [AGENT.md](AGENT.md#3-canonical-folder-ownership)
for placement rules.

## Development expectations

- Validate request bodies, path values, and query parameters before writes; use
  consistent errors and roll back failed transactions.
- Write unit tests for business logic, API tests for the contract, and isolated
  integration tests for persistence. Cover success and failure paths.
- Explain intent and non-obvious behavior with comments and multiline docstrings.
  Use readable multiline formatting and type hints.
- Keep credentials out of source control and logs. Follow the
  [secrets management guide](docs/SECRETS_MANAGEMENT.md).
- Keep documentation and relevant [agent instructions](AGENT.md) synchronized
  when requirements change.

Use the [API specification](docs/api.md) when adding business routes. Add
verified migration and deployment commands here when those workflows exist.

## Documentation

- [Local stack launcher](docs/local-development.md): one Bash entry point for
  Windows PostgreSQL, FastAPI, and React, with prerequisite checks and cleanup.

- [Local PostgreSQL](docs/local-postgresql.md): Windows startup, private settings,
  and database readiness verification.

- [Ubuntu host monitoring](docs/ubuntu-monitoring.md) covers setup and verification
  for the API, local PostgreSQL, and the host collector.

- [Ubuntu accounts and permissions](docs/ubuntu-accounts.md) covers provisioning
  separate junior and senior workspace access.

- [Discord alerts](docs/discord-alerts.md) covers private webhook setup and
  demonstrates a scheduled disk usage notification.
- [Docker deployment](docs/docker-deployment.md) covers the Compose services,
  persistence, host monitoring, and the domain handoff.
- [Git and GitHub Actions workflow](docs/github-actions-plan.md) covers branches,
  review, and the CI checks.
- [Project plan and progress](docs/project-plan.md): current status, milestones,
  assignment coverage, and next steps.
- [Presentation guide](docs/presentation-guide.md): the recorded demo in order,
  with commands, what they do, and talking points.

- [Frontend development](docs/frontend.md): startup, demo/live data, verification,
  and integration limitations.
- [API specification](docs/api.md): endpoint contracts, examples, errors, testing,
  and code explanation requirements.
- [Secrets management](docs/SECRETS_MANAGEMENT.md): credential storage and handling.
- [Agent instructions](AGENT.md): architecture, working conventions, and demo
  constraints.
