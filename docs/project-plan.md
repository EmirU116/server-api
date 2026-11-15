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
| 1. Local backend foundation | Python dependency manifest, application entry point, configuration, structured error handling, test setup, documented local startup | App starts locally; smoke tests run; missing configuration fails clearly without exposing secrets |
| 2. Persistence and read endpoints | PostgreSQL connection, SQLAlchemy models, Alembic migrations, health and server GET routes | Migrations apply to an isolated database; health reports dependency failure; server identity describes the host correctly |
| 3. Metrics and incidents | Auth/permissions, metrics GET/POST, full incident CRUD, pagination and validation | Unit and API contract tests cover the matrix in `api.md`; database integration tests prove persistence and rollback |
| 4. Monitoring and recovery | Host collector, Cron schedules, threshold detection, alert delivery, PostgreSQL/log backup and restore scripts | A collected sample is stored; a controlled breach produces an incident and alert without duplicate open incidents; isolated restore succeeds |
| 5. Native EC2 deployment — G | Bootstrap via SCP, repository setup, independent student SSH access, native service, Nginx, scheduled operations | Rehearsed fresh-instance deployment; API/database connectivity, restart behavior, monitoring, and backups demonstrated |
| 6. Containers and HTTPS — VG | API Dockerfile, separate API/PostgreSQL Compose services, persistent volume, domain, Certbot | Compose validation and health checks pass; records survive restart; HTTPS and renewal checks pass; native service stopped before port reuse |
| 7. Frontend | React/TypeScript app, typed API client, health/metrics/server views, incident management | Type checking/build pass; UI handles loading, empty, validation, permission, and unavailable states; core flows work against the API |
| 8. Demo preparation | Deployment runbook, requirement checklist, timed rehearsal, evidence and speaking roles | Both students complete and explain a fresh-instance rehearsal within the 60-minute limit |

Frontend work depends on a stable API contract and working endpoints. A minimal
UI may be developed after phase 3 if it does not delay G/VG delivery. GitHub
Actions CI/CD remains an optional follow-up; local verification is required
regardless of whether CI exists.

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
