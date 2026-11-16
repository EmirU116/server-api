# ServerWatch project plan and progress

Last reviewed: 2026-11-16. Status is based on repository inspection, not a live
EC2 audit. This is the progress tracker; endpoint details remain in
[the API specification](api.md).

## Current position

**Stage: local FastAPI foundation verified. Next milestone: persistence and read endpoints.**

The project has a runnable FastAPI application factory, validated settings,
shared error handling, dependency manifests, and a passing foundation test suite.
Swagger/ReDoc and OpenAPI are available locally; the four business API groups
remain unimplemented. There are no database migrations, container configuration,
or deployment automation yet. No cloud deployment or assignment demonstration
has been verified.

| Workstream | Current status | Evidence |
| --- | --- | --- |
| Project scope and API design | Documented; not implemented | `README.md`, `docs/api.md` |
| Organization and security guidance | Documented | `docs/FOLDER_STRUCTURE.md`, `docs/SECRETS_MANAGEMENT.md` |
| Agent workflows | Instructions present | `AGENT.md`, `.agents/skills/` |
| Backend foundation and tests | Verified | `backend/app/main.py`, `backend/app/core/`, `backend/tests/`; verification below |
| Business endpoints and persistence | Not started | API/model/migration directories remain placeholders |
| React frontend | Not started | `frontend/.gitkeep` |
| Infrastructure and CI/CD | Not started | Placeholder directories only |
| Deployment and demo | Not verified | No runbook or recorded verification evidence |

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

Course requirements below are taken from the project's agent instructions. The
original assignment brief is not present in the repository; confirm assessment
details against it before finalizing the demonstration. No ICM migration is
assumed by this plan.

## Implementation milestones

Phase 1 is **Verified**; phases 2–8 are **Not started**. Complete each with
observable evidence, not only source files. Phases express dependencies, not
calendar estimates; owners and deadlines have not been assigned.

| Phase | Deliverables | Completion evidence | Status |
| --- | --- | --- | --- |
| 1. Local backend foundation (Python, FastAPI, pytest) | Python dependency manifest, application entry point, configuration, structured error handling, test setup, documented local startup | App starts locally; smoke tests pass; invalid configuration fails without exposing values. No required credentials exist at this stage | Verified |
| 2. Persistence and read endpoints (Python, PostgreSQL, Alembic) | PostgreSQL connection, SQLAlchemy models, Alembic migrations, health and server GET routes | Migrations apply to an isolated database; health reports dependency failure; server identity describes the host correctly | Not started |
| 3. Metrics and incidents (Python, FastAPI, pytest) | Auth/permissions, metrics GET/POST, full incident CRUD, pagination and validation | Unit and API contract tests cover the matrix in `api.md`; database integration tests prove persistence and rollback | Not started |
| 4. Monitoring and recovery (Bash, Cron, Python, PostgreSQL) | Host collector, Cron schedules, threshold detection, alert delivery, PostgreSQL/log backup and restore scripts | A collected sample is stored; a controlled breach produces an incident and alert without duplicate open incidents; isolated restore succeeds | Not started |
| 5. Native EC2 deployment — G (AWS EC2, Bash, systemd, Nginx) | Bootstrap via SCP, repository setup, independent student SSH access, native service, Nginx, scheduled operations | Rehearsed fresh-instance deployment; API/database connectivity, restart behavior, monitoring, and backups demonstrated | Not started |
| 6. Containers and HTTPS — VG (Docker, Docker Compose, DNS, Certbot) | API Dockerfile, separate API/PostgreSQL Compose services, persistent volume, domain, Certbot | Compose validation and health checks pass; records survive restart; HTTPS and renewal checks pass; native service stopped before port reuse | Not started |
| 7. Frontend (React, TypeScript) | React/TypeScript app, typed API client, health/metrics/server views, incident management | Type checking/build pass; UI handles loading, empty, validation, permission, and unavailable states; core flows work against the API | Not started |
| 8. Demo preparation (Documentation, Deployment, Presentation) | Deployment runbook, requirement checklist, timed rehearsal, evidence and speaking roles | Both students complete and explain a fresh-instance rehearsal within the 60-minute limit | Not started |

Frontend work depends on a stable API contract and working endpoints. A minimal
UI may be developed after phase 3 if it does not delay G/VG delivery. GitHub
Actions CI/CD remains an optional follow-up; local verification is required
regardless of whether CI exists.

### Tasks by topic

Each row is a task within the corresponding milestone. Topics identify the
language, tool, or work area involved and appear in parentheses beside each
task name. A task can involve several topics.
Tasks 1.1–1.3 are **Verified**; the remaining tasks are **Not started**. Each
task uses the completion evidence for its parent milestone above.

| Task (topics) | Work to complete | Status |
| --- | --- | --- |
| 1.1 Backend setup (Python, FastAPI) | Add dependencies, application entry point, and local configuration. | Verified |
| 1.2 Errors and test foundation (Python, Pydantic, pytest) | Add structured error handling and test setup; verify startup and configuration failure paths. | Verified |
| 1.3 Local development guide (Documentation) | Document verified installation, startup, and test commands. | Verified |
| 2.1 Database connection and schema (Python, PostgreSQL, SQLAlchemy, Alembic) | Add database sessions, models, and versioned migrations. | Not started |
| 2.2 Health and server endpoints (Python, FastAPI, Linux) | Implement health and server GET routes, including dependency failure and correct host identity. | Not started |
| 2.3 Persistence verification (Python, pytest, PostgreSQL) | Test migrations and database connectivity using an isolated database. | Not started |
| 3.1 Authentication and validation (Python, FastAPI, Pydantic, Security) | Implement the documented roles, input constraints, and consistent errors. | Not started |
| 3.2 Metrics endpoints (Python, FastAPI, PostgreSQL) | Implement metrics GET/POST, filtering, pagination, and persistence. | Not started |
| 3.3 Incident endpoints (Python, FastAPI, PostgreSQL) | Implement incident create, read, update, and delete behavior. | Not started |
| 3.4 API and business logic tests (Python, pytest, PostgreSQL) | Cover the API contract, permissions, validation, transactions, and rollback. | Not started |
| 4.1 Host metrics collection (Bash, Linux, HTTP) | Collect host statistics and submit them to the authenticated metrics endpoint. | Not started |
| 4.2 Scheduled collection (Cron, Linux) | Configure collection schedules and verify execution. | Not started |
| 4.3 Incident detection and alerts (Python, Monitoring) | Detect threshold breaches, avoid duplicate open incidents, and deliver alerts through the selected channel. | Not started |
| 4.4 Backup and restore (Bash, PostgreSQL, Cron) | Script database/log backups, schedule them, and verify an isolated restore. | Not started |
| 5.1 EC2 and student access (AWS EC2, Linux, SSH) | Prepare the instance configuration and independent access for both students. | Not started |
| 5.2 Server bootstrap (Bash, SCP, Git, Linux) | Transfer and run bootstrap automation, install prerequisites, and clone the repository. | Not started |
| 5.3 Native service and reverse proxy (systemd, Nginx, Linux) | Run FastAPI as a native service and configure public request forwarding. | Not started |
| 5.4 Native deployment verification (Bash, Linux, Testing) | Verify connectivity, restarts, scheduled monitoring, and backups on a fresh instance. | Not started |
| 6.1 API image (Docker, Python) | Create the API Dockerfile and build a runnable image. | Not started |
| 6.2 Container services and storage (Docker Compose, PostgreSQL) | Configure separate API/database services, private networking, health checks, and persistent storage. | Not started |
| 6.3 Domain and TLS (DNS, Nginx, Certbot, HTTPS) | Configure the custom domain, certificate, redirects, and renewal. | Not started |
| 6.4 Container deployment verification (Docker Compose, Testing) | Validate configuration, health, and persistence; stop the native API before reusing its port. | Not started |
| 7.1 Frontend foundation (React, TypeScript) | Set up the frontend project and typed API client. | Not started |
| 7.2 Dashboard and incident management (React, TypeScript, CSS) | Build health, metrics, server, and incident views with the required UI states. | Not started |
| 7.3 Frontend verification (TypeScript, Frontend testing) | Run type checking/build and verify core UI flows against the API. | Not started |
| 8.1 Runbook and assessment checklist (Documentation) | Record deployment steps, requirement evidence, and speaking roles. | Not started |
| 8.2 Timed pair rehearsal (AWS EC2, Deployment, Presentation) | Rehearse from a fresh instance within 60 minutes, with both students explaining their work. | Not started |
| Optional: CI/CD (GitHub Actions, YAML, Testing, Docker) | Automate verified tests/builds after the required milestones are stable; deployment remains subject to approval. | Not started |

Python tasks include unit tests and clear comments or multiline docstrings for
non-obvious behavior. Bash tasks include syntax checks and failure-path checks;
Docker tasks include build/configuration and runtime checks as applicable.
Keep task status and evidence alongside these rows when implementation begins.

## Assignment coverage tracker

All rows are currently **pending**.

| Requirement recorded in the project | Planned phase | Evidence to retain |
| --- | --- | --- |
| G: fresh EC2 instance, appropriate AMI/security groups, Elastic IP | 5, 8 | Provisioning steps and recorded instance creation |
| G: independent SSH access for both students | 5, 8 | Both students demonstrate their own access without exposing keys |
| G: Bash bootstrap transferred with SCP and repository cloned | 5 | Runbook and successful bootstrap output |
| G: FastAPI connected to PostgreSQL, native service, Nginx | 2–5 | Request results, service status, proxy configuration check |
| G: Cron PostgreSQL/log backups and monitoring with alerts | 4–5 | Schedule, backup/restore results, controlled alert demonstration |
| VG: FastAPI and PostgreSQL in separate Compose services | 6 | Configuration validation, service health, persistence checks |
| VG: custom domain and HTTPS through Certbot | 6 | DNS/HTTPS checks and renewal verification |
| Pair recording: new instance created during a maximum 60-minute demo | 8 | Timed rehearsal and final recording checklist |

Confirm Elastic IP allocation timing against the course rules. Prepare scripts
and templates beforehand, but create the demonstration instance during recording.
Rehearsal instances are separate from the final demonstration instance.

## Decisions to settle before implementation

- Confirm the original assignment brief, deadline, and division of work between
  the two students.
- Choose credential provisioning for the roles defined by `api.md`. That contract
  specifies bearer authentication; the secrets guide contains an older
  `X-API-Key`/unversioned metrics example. Align collector documentation with the
  contract before implementing authentication.
- Define metric collection frequency, incident thresholds, resolution policy,
  retention, and the chosen notification channel. These are not yet specified.
- Choose how a containerized API obtains the monitored host's identity and
  health without reporting only its own container metadata.
- Identify domain/DNS ownership, backup storage location, and recovery procedure.
  Local backups alone do not protect against losing the instance.

## Immediate next task

Start task **2.1 Database connection and schema (Python, PostgreSQL, SQLAlchemy,
Alembic)**: add isolated local database configuration, sessions, models, and
migrations. Follow with real health/server endpoints and persistence checks.
Authentication, frontend, and live deployment remain later tasks.

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
full business endpoints, authentication, Docker, AWS, or frontend checks have
been performed. See [the README](../README.md#local-backend-setup-python-fastapi)
for local setup and verification commands.

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
