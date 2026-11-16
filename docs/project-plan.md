# ServerWatch project plan and progress

Last reviewed: 2026-11-16. Status is based on repository inspection, not a live
EC2 audit. This is the progress tracker; endpoint details remain in
[the API specification](api.md).

## Current position

**Stage: planning and scaffolding. Next milestone: a runnable local backend.**

The project has a defined API contract, architecture guidance, and placeholder
directories. There is no executable application, dependency manifest, database
migration, test suite, container configuration, or deployment automation yet.
No cloud deployment or assignment demonstration has been verified.

| Workstream | Current status | Evidence |
| --- | --- | --- |
| Project scope and API design | Documented; not implemented | `README.md`, `docs/api.md` |
| Organization and security guidance | Documented | `docs/FOLDER_STRUCTURE.md`, `docs/SECRETS_MANAGEMENT.md` |
| Agent workflows | Instructions present | `AGENT.md`, `.agents/skills/` |
| Backend, persistence, and tests | Not started | Only `.gitkeep` files in backend directories |
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

All milestones below are **not started**. Complete each with observable evidence,
not only source files. Phases express dependencies, not calendar estimates;
owners and deadlines have not been assigned.

| Phase | Deliverables | Completion evidence |
| --- | --- | --- |
| 1. Local backend foundation (Python, FastAPI, pytest) | Python dependency manifest, application entry point, configuration, structured error handling, test setup, documented local startup | App starts locally; smoke tests run; missing configuration fails clearly without exposing secrets |
| 2. Persistence and read endpoints (Python, PostgreSQL, Alembic) | PostgreSQL connection, SQLAlchemy models, Alembic migrations, health and server GET routes | Migrations apply to an isolated database; health reports dependency failure; server identity describes the host correctly |
| 3. Metrics and incidents (Python, FastAPI, pytest) | Auth/permissions, metrics GET/POST, full incident CRUD, pagination and validation | Unit and API contract tests cover the matrix in `api.md`; database integration tests prove persistence and rollback |
| 4. Monitoring and recovery (Bash, Cron, Python, PostgreSQL) | Host collector, Cron schedules, threshold detection, alert delivery, PostgreSQL/log backup and restore scripts | A collected sample is stored; a controlled breach produces an incident and alert without duplicate open incidents; isolated restore succeeds |
| 5. Native EC2 deployment — G (AWS EC2, Bash, systemd, Nginx) | Bootstrap via SCP, repository setup, independent student SSH access, native service, Nginx, scheduled operations | Rehearsed fresh-instance deployment; API/database connectivity, restart behavior, monitoring, and backups demonstrated |
| 6. Containers and HTTPS — VG (Docker, Docker Compose, DNS, Certbot) | API Dockerfile, separate API/PostgreSQL Compose services, persistent volume, domain, Certbot | Compose validation and health checks pass; records survive restart; HTTPS and renewal checks pass; native service stopped before port reuse |
| 7. Frontend (React, TypeScript) | React/TypeScript app, typed API client, health/metrics/server views, incident management | Type checking/build pass; UI handles loading, empty, validation, permission, and unavailable states; core flows work against the API |
| 8. Demo preparation (Documentation, Deployment, Presentation) | Deployment runbook, requirement checklist, timed rehearsal, evidence and speaking roles | Both students complete and explain a fresh-instance rehearsal within the 60-minute limit |

Frontend work depends on a stable API contract and working endpoints. A minimal
UI may be developed after phase 3 if it does not delay G/VG delivery. GitHub
Actions CI/CD remains an optional follow-up; local verification is required
regardless of whether CI exists.

### Tasks by topic

Each row is a task within the corresponding milestone. Topics identify the
language, tool, or work area involved and appear in parentheses beside each
task name. A task can involve several topics.
All tasks below are **not started** and use the completion evidence for their
parent milestone above.

| Task (topics) | Work to complete |
| --- | --- |
| 1.1 Backend setup (Python, FastAPI) | Add dependencies, application entry point, and local configuration. |
| 1.2 Errors and test foundation (Python, Pydantic, pytest) | Add structured error handling and test setup; verify startup and configuration failure paths. |
| 1.3 Local development guide (Documentation) | Document verified installation, startup, and test commands. |
| 2.1 Database connection and schema (Python, PostgreSQL, SQLAlchemy, Alembic) | Add database sessions, models, and versioned migrations. |
| 2.2 Health and server endpoints (Python, FastAPI, Linux) | Implement health and server GET routes, including dependency failure and correct host identity. |
| 2.3 Persistence verification (Python, pytest, PostgreSQL) | Test migrations and database connectivity using an isolated database. |
| 3.1 Authentication and validation (Python, FastAPI, Pydantic, Security) | Implement the documented roles, input constraints, and consistent errors. |
| 3.2 Metrics endpoints (Python, FastAPI, PostgreSQL) | Implement metrics GET/POST, filtering, pagination, and persistence. |
| 3.3 Incident endpoints (Python, FastAPI, PostgreSQL) | Implement incident create, read, update, and delete behavior. |
| 3.4 API and business logic tests (Python, pytest, PostgreSQL) | Cover the API contract, permissions, validation, transactions, and rollback. |
| 4.1 Host metrics collection (Bash, Linux, HTTP) | Collect host statistics and submit them to the authenticated metrics endpoint. |
| 4.2 Scheduled collection (Cron, Linux) | Configure collection schedules and verify execution. |
| 4.3 Incident detection and alerts (Python, Monitoring) | Detect threshold breaches, avoid duplicate open incidents, and deliver alerts through the selected channel. |
| 4.4 Backup and restore (Bash, PostgreSQL, Cron) | Script database/log backups, schedule them, and verify an isolated restore. |
| 5.1 EC2 and student access (AWS EC2, Linux, SSH) | Prepare the instance configuration and independent access for both students. |
| 5.2 Server bootstrap (Bash, SCP, Git, Linux) | Transfer and run bootstrap automation, install prerequisites, and clone the repository. |
| 5.3 Native service and reverse proxy (systemd, Nginx, Linux) | Run FastAPI as a native service and configure public request forwarding. |
| 5.4 Native deployment verification (Bash, Linux, Testing) | Verify connectivity, restarts, scheduled monitoring, and backups on a fresh instance. |
| 6.1 API image (Docker, Python) | Create the API Dockerfile and build a runnable image. |
| 6.2 Container services and storage (Docker Compose, PostgreSQL) | Configure separate API/database services, private networking, health checks, and persistent storage. |
| 6.3 Domain and TLS (DNS, Nginx, Certbot, HTTPS) | Configure the custom domain, certificate, redirects, and renewal. |
| 6.4 Container deployment verification (Docker Compose, Testing) | Validate configuration, health, and persistence; stop the native API before reusing its port. |
| 7.1 Frontend foundation (React, TypeScript) | Set up the frontend project and typed API client. |
| 7.2 Dashboard and incident management (React, TypeScript, CSS) | Build health, metrics, server, and incident views with the required UI states. |
| 7.3 Frontend verification (TypeScript, Frontend testing) | Run type checking/build and verify core UI flows against the API. |
| 8.1 Runbook and assessment checklist (Documentation) | Record deployment steps, requirement evidence, and speaking roles. |
| 8.2 Timed pair rehearsal (AWS EC2, Deployment, Presentation) | Rehearse from a fresh instance within 60 minutes, with both students explaining their work. |
| Optional: CI/CD (GitHub Actions, YAML, Testing, Docker) | Automate verified tests/builds after the required milestones are stable; deployment remains subject to approval. |

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

Implement phase 1: create the Python backend foundation and test setup, then add
verified local installation, startup, and test commands to the README. Do not
add frontend or live deployment work to that first task.

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
