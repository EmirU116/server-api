# ServerWatch

ServerWatch is a server monitoring and incident management platform for an MLOps
course assignment. It is intended to monitor one Ubuntu server on AWS EC2,
store resource measurements, and expose an API for inspecting server health,
server information, and operational incidents.

The project aims to meet the course's G/VG deployment requirements while keeping
the implementation understandable, maintainable, and suitable for a portfolio.

## Current status

The FastAPI foundation now includes an application factory, validated runtime
settings, consistent error handling, dependency manifests, and automated tests.
Local interactive documentation is available at `/docs` and `/redoc`.

The four business API groups below are still planned. Database models,
migrations, authentication, monitoring, containers, and deployment configuration
have not been implemented. The application does not yet report server health.

See the [project plan and progress tracker](docs/project-plan.md) for the current
stage, implementation milestones, and assignment coverage.

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
The route list is intentionally empty until the business endpoints are
implemented. A `404` at `/` or `/api/v1/health` is expected at this stage.
Use `--reload` for local development only. Stop the server with `Ctrl+C`.

No database or credentials are needed for this foundation. Settings come from
environment variables:

| Variable | Default | Allowed values |
| --- | --- | --- |
| `SERVERWATCH_APP_NAME` | `ServerWatch` | Nonblank name, at most 100 characters |
| `SERVERWATCH_ENVIRONMENT` | `development` | `development`, `test`, `production` |

Invalid settings prevent startup with a sanitized error. There are no required
credentials yet; add fail-fast validation when database/authentication settings
are introduced. Production mode disables Swagger, ReDoc, and OpenAPI endpoints.
It does not turn this foundation into a complete production deployment.

For optional local overrides, copy `.env.example` to an ignored `.env` and load
it explicitly:

```bash
cp .env.example .env
python -m uvicorn app.main:create_app --factory --app-dir backend --env-file .env --reload --host 127.0.0.1 --port 8000
```

Only copy the template when creating a new local configuration; preserve any
existing `.env`. Never commit real credentials. Tests do not load dotenv files.

Run checks from the repository root with the virtual environment active:

```bash
python -m pytest backend/tests -q
python -m ruff check backend
python -m ruff format --check backend
python -m pip check
```

Tests cover documentation exposure, configuration, shared HTTP errors, malformed
JSON, validation, and sanitized unexpected route failures. Sample routes exist
only in tests. Persistence and the full API test matrix remain future work.
Shared handlers follow [FastAPI's exception handling guidance](https://fastapi.tiangolo.com/tutorial/handling-errors/);
configuration uses [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).
Streaming responses and background jobs, if introduced, will need separate
failure handling because they can fail after response headers have been sent.

## API scope

All routes use the `/api/v1` prefix and target a single monitored server.

| API | Methods and paths | Responsibility |
| --- | --- | --- |
| Health | `GET /health` | Report server and required dependency health. |
| Metrics | `GET /metrics`, `POST /metrics` | Read stored statistics and accept CPU, memory, disk, and uptime samples. |
| Server | `GET /server` | Return the server name, hostname, operating system, and architecture. |
| Incidents | `POST /incidents`, `GET /incidents`, `GET /incidents/{incident_id}`, `PATCH /incidents/{incident_id}`, `DELETE /incidents/{incident_id}` | Create, list, read, update, and delete incident records. |

The [API specification](docs/api.md) defines payloads, validation, authentication,
permissions, pagination, error responses, and required tests. Health is public;
the remaining endpoints require authentication under the proposed contract.
Automatic threshold detection and alert delivery are broader project goals,
separate from the initial incident CRUD contract.

## Planned architecture

```text
Client -> HTTPS -> Nginx on EC2 -> FastAPI/Uvicorn -> PostgreSQL

Cron -> Host metrics collector -> Authenticated metrics API -> PostgreSQL
```

The monitoring workflow will also support incident detection and Discord/email
alerts. PostgreSQL will store measurements and incidents, with persistent storage
and versioned migrations. The public entry point will be Nginx; PostgreSQL will
remain on a private network.

| Area | Intended tools |
| --- | --- |
| API and validation | Python, FastAPI, Pydantic |
| Frontend | React with TypeScript |
| Persistence | PostgreSQL, SQLAlchemy, Alembic |
| Host automation | Ubuntu EC2, Bash, Cron |
| Service and containers | systemd for the native service demonstration; Docker Compose for the final container deployment |
| Web access | Nginx, Certbot, HTTPS |
| Testing | pytest, API contract tests, isolated database integration tests |
| Optional extensions | GitHub Actions CI/CD and a React dashboard |

## Assignment and demonstration

The requirements recorded in [AGENT.md](AGENT.md#10-course-requirements-and-demonstration-constraints)
include:

- **G:** provision a new EC2 instance, provide independent SSH access for both
  students, transfer and run a Bash bootstrap script, clone the repository,
  connect FastAPI to PostgreSQL, demonstrate a native service using systemd or
  supervisor, configure Nginx, and schedule backups, monitoring, and alerts.
- **VG:** run FastAPI and PostgreSQL in separate Docker Compose services and
  provide a custom domain with HTTPS using Certbot.
- **Recorded pair demo:** a maximum of 60 minutes, with the EC2 instance created
  from scratch during recording. Both students must explain their work.

These are project-recorded requirements; consult the course assignment for the
authoritative assessment criteria. CI/CD and a frontend are optional extensions.

## Repository layout

```text
backend/
  app/main.py          FastAPI application factory
  app/core/            Runtime settings and shared error handling
  app/api/             API route scaffold
  app/models/          Database model scaffold
  app/schemas/         Request and response schema scaffold
  app/services/        Business logic scaffold
  alembic/             Migration scaffold
  tests/               Foundation unit and API tests
  requirements.txt     Runtime dependencies
  requirements-dev.txt Test and lint dependencies
  pyproject.toml       pytest and Ruff configuration
frontend/              Reserved for an optional UI
infrastructure/        Nginx, Cron, systemd, and script scaffolds
.github/workflows/     Reserved for CI/CD
.agents/skills/        Repository agent workflows
docs/                  Specifications and project guides
AGENT.md               Agent instructions and project constraints
```

See the [folder structure guide](docs/FOLDER_STRUCTURE.md) for placement rules
and the recommended structure as implementation grows.

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

- [Project plan and progress](docs/project-plan.md): current status, milestones,
  assignment coverage, and next steps.

- [API specification](docs/api.md): endpoint contracts, examples, errors, testing,
  and code explanation requirements.
- [Folder structure](docs/FOLDER_STRUCTURE.md): file ownership and organization.
- [Secrets management](docs/SECRETS_MANAGEMENT.md): credential storage and handling.
- [Agent instructions](AGENT.md): architecture, working conventions, and demo
  constraints.
