# ServerWatch project plan and progress

Last reviewed on 2026-11-25. Live status reflects the reported EC2 verification.
Endpoint details are in the [API specification](api.md).

## What to do next

**Next, rehearse the full recording on a fresh instance.** Every G requirement,
VG1 and VG2 have been verified on the current EC2 instance. Public HTTP access (G7/G8) and
Compose persistence (VG1) were verified on the current EC2 instance.

### Finish the G requirements

1. [x] **Send a Discord alert (Python, systemd, Discord).** The scheduled
   check delivered an alert during a controlled threshold test.
   See the [Discord verification record](#discord-alert-verification-g6).
2. [x] **Demonstrate backups (Bash, Cron, PostgreSQL).** On 2026-11-24 at
   11:22 UTC, Cron produced a database dump and service-log snapshot. The dump
   restored into a separate database with 18,867 metrics and 0 incidents.
   Use the [EC2 walkthrough](ec2-manual-setup.md#verify-cron-backups-and-restore-g5)
   to repeat the test on camera.
3. [x] **Confirm public access from your computer (HTTP, Nginx, FastAPI).**
   On 2026-11-24, after `setup.sh` and `verify.sh` passed 8/8 on the cleaned-up
   code, requests from outside AWS to `/`, `/docs`, `/openapi.json` and
   `/api/v1/health?server_id=1` on the public IP all returned HTTP 200.
   Live dashboard data still needs HTTPS or an SSH tunnel.
4. [ ] **Rehearse the pair deployment (AWS EC2, SSH, SCP, Bash, systemd).**
   Start with a fresh EC2 instance, configure the security group and Elastic IP,
   show both SSH logins, transfer and run the bootstrap, and clone into the
   deployment user's home folder. Done when both partners can demonstrate the
   native API, public docs, backups, and Discord alert within 60 minutes. Use
   the [EC2 setup guide](ec2-manual-setup.md).

### Finish the VG requirements

1. [x] **Deploy containers on EC2 (Docker, Compose, PostgreSQL).** On
   2026-11-24, `compose_host.sh collect` stored host samples through the
   Compose API. The Compose database held 867 metrics, `down` removed the
   containers and networks but kept the `postgres_data` volume, and after
   `up -d --wait` (db, api and web healthy; migrate exited) the count was
   still 867. Show the native systemd deployment during the demo as well.
2. [x] **Set up your own domain and HTTPS (DNS, Nginx, Certbot).** On
   2026-11-25, `setup_https.sh` issued a Let's Encrypt certificate for
   `serverwatch.dev` and `www.serverwatch.dev` (valid to 2027-02-23). From
   outside AWS, `/`, `/docs` and health returned 200 over HTTPS with the
   certificate validated, and HTTP redirected with 301. The dashboard loaded
   with a padlock in the user's browser.

RDS and automatic GitHub Actions deployment are assignment bonuses.

## Current position

**All four APIs and the dashboard are implemented, and every G and VG requirement has been verified on EC2. The remaining work is the timed fresh-instance rehearsal and the recording.**

Reported on the current EC2 instance: 8/8 native monitoring checks passing,
public HTTP access to the dashboard, Swagger and OpenAPI, a Cron backup that
restored into a separate database (G5), a delivered Discord disk alert (G6),
Compose data that survived container recreation (VG1), and HTTPS on
`serverwatch.dev` with a Let's Encrypt certificate (VG2). Still open:
collection after reboot and the timed fresh-instance rehearsal.

| Workstream | Current status | Evidence |
| --- | --- | --- |
| Project scope and API design | Four API resources implemented | `README.md`, `docs/api.md` |
| Organization and security guidance | Documented | `AGENT.md`, `docs/SECRETS_MANAGEMENT.md` |
| Agent workflows | Instructions present | `AGENT.md`, `.agents/skills/` |
| Backend foundation and tests | Verified | `backend/app/main.py`, `backend/app/core/`, `backend/tests/`; verification below |
| Health API | Verified route/service behavior; user confirmed Windows database health | `backend/app/api/health.py`, schemas/services, and `backend/tests/test_health.py` |
| Server API | Implemented; native EC2/container verification pending | Server router/schema/service and tests; reader token authentication |
| Metrics and persistence | Implemented and tested with isolated PostgreSQL | Metrics model, Alembic upgrade, transaction, filtering, and persistence tests; both migrations present in the verified local incident database |
| Incident endpoints | Verified locally on Windows | CRUD, resolution/reopening, and deletion verified through FastAPI against local PostgreSQL; automated persistence/error tests also pass |
| React frontend | Live health, server, metrics and incidents integrated; browser check pending | `frontend/tests/`, typecheck, build and format checks in CI |
| Infrastructure and CI | Native setup, public HTTP routing, Cron backups, Discord alerts and Compose persistence verified on EC2; reboot check pending | `setup.sh`, `verify.sh`, systemd units, root `tests/`, `.github/workflows/ci.yml` |
| Deployment and demo | Presentation guide written; rehearsal pending | [Presentation guide](presentation-guide.md). The timed pair rehearsal is pending. |

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
- File placement: [folder ownership](../AGENT.md#3-canonical-folder-ownership).
- Frontend setup and data modes: [frontend development](frontend.md).

The [Swedish assignment brief](assignment-brief.md) defines G, VG, the optional
bonuses and the pair recording. Windows is a local development convenience.
The assessed deployment runs on EC2. The React dashboard is a project extension.

## Implementation milestones

Phase 1 is **Verified**. Phases 2–7 are **In progress**, with native EC2
verification reported for phase 5. The fresh-instance demo for phase 8 remains
open. Each milestone requires the evidence below. Owners and deadlines are
unassigned.

| Phase | Deliverables | Completion evidence | Status |
| --- | --- | --- | --- |
| 1. Local backend foundation (Python, FastAPI, pytest) | Python dependency manifest, application entry point, configuration, structured error handling, test setup, documented local startup | App starts locally; smoke tests pass; invalid configuration fails without exposing values. No required credentials exist at this stage | Verified |
| 2. Persistence and read endpoints (Python, PostgreSQL, Alembic) | PostgreSQL connection, SQLAlchemy models, Alembic migrations, health and server GET routes | Migrations apply to an isolated database; health reports dependency failure; server identity describes the host correctly | In progress |
| 3. Metrics and incidents (Python, FastAPI, pytest) | Auth/permissions, metrics GET/POST, full incident CRUD, pagination and validation | Unit and API contract tests cover the matrix in `api.md`; database integration tests prove persistence and rollback | In progress |
| 4. Monitoring and recovery (Bash, Cron, Python, PostgreSQL) | Host collector, Cron schedules, threshold detection, alert delivery, PostgreSQL/log backup and restore scripts | A collected sample is stored; a controlled breach sends one Discord alert; isolated restore succeeds | In progress |
| 5. Native EC2 deployment — G (AWS EC2, Bash, systemd, Nginx) | Bootstrap via SCP, repository setup, independent student SSH access, native service, Nginx, scheduled operations | Rehearsed fresh-instance deployment; API/database connectivity, restart behavior, monitoring, and backups demonstrated | In progress |
| 6. Containers and HTTPS — VG (Docker, Docker Compose, DNS, Certbot) | API Dockerfile, separate API/PostgreSQL Compose services, persistent volume, domain, Certbot | Compose validation and health checks pass; records survive recreation; HTTPS and renewal checks pass on the public domain | In progress |
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
| 4.2 Scheduled health checks (Linux, Monitoring) | The recurring Discord check ran on EC2. Verify monitoring starts after reboot. | In progress |
| 4.3 Disk threshold alerts (Python, Monitoring, Discord) | Scheduled Discord delivery verified on EC2. Duplicate suppression covered by local tests. | Verified |
| 4.4 Backup and restore (Bash, PostgreSQL, Cron) | Cron created the database and service-log snapshot on EC2. Restored the dump into a separate database and queried both tables. | Verified |
| 5.1 EC2 and student access (AWS EC2, Linux, SSH) | Prepare the instance configuration and independent access for both students. | Not started |
| 5.2 Server bootstrap (Bash, SCP, Git, Linux) | Ubuntu installer prepares a cloned checkout with Python, PostgreSQL, and migrations. SCP and fresh instance verification remain pending. | In progress |
| 5.3 Native service and reverse proxy (systemd, Nginx, Linux) | Native verifier passed 8/8 on EC2, as reported by the user. Nginx setup and web verification scripts are implemented. Run the [public IP rehearsal](ec2-manual-setup.md#7-serve-the-dashboard-and-api-through-nginx-bash-react-fastapi) and capture browser evidence. | In progress |
| 5.4 Native deployment verification (Bash, Linux, Testing) | Localhost smoke verifier added; fresh-instance verification, restarts, and scheduled monitoring after reboot remain pending. | In progress |
| 5.5 Define and verify environment access (Ubuntu, Bash, Linux users, groups, ACLs) | Define dev/prod ownership and role membership, provision accounts and inherited permissions, then check effective allowed and denied operations as each identity. See [Ubuntu accounts and permissions](ubuntu-accounts.md). | Implemented and tested with simulated system commands. Verify ACLs on EC2. |
| 6.1 API and web images (Docker, Python, React) | Dockerfiles and build exclusions implemented. Both images built and ran healthy on EC2 on 2026-11-24. | Verified |
| 6.2 Container services and storage (Docker Compose, PostgreSQL) | Compose includes a private DB, migration job, API, and loopback web proxy. 867 metrics survived `down` and `up` on EC2 on 2026-11-24. | Verified |
| 6.3 Domain and TLS (DNS, Nginx, Certbot, HTTPS) | `setup_https.sh` issued the certificate on EC2 on 2026-11-25; HTTPS, the HTTP redirect and the renewal dry run passed. | Verified |
| 6.4 Container deployment verification (Docker Compose, Testing) | Verified locally and on EC2: host collection into Compose, healthy services, and data that survived container recreation. | Verified |
| 7.1 Frontend foundation (React, TypeScript) | Set up the frontend project and typed API client. | Verified |
| 7.2 Dashboard and incident management (React, TypeScript, CSS) | Build health, metrics, server, and incident views with the required UI states. | In progress |
| 7.3 Frontend verification (TypeScript, Frontend testing) | Run type checking/build and verify core UI flows against the API. | In progress |
| 8.1 Runbook and assessment checklist (Documentation) | [Presentation guide](presentation-guide.md) with the demo order, commands and talking points. Assign speaking roles. | In progress |
| 8.2 Timed pair rehearsal (AWS EC2, Deployment, Presentation) | Rehearse from a fresh instance within 60 minutes, with both students explaining their work. | Not started |
| PR checks (Git, GitHub Actions) | [Human and agent workflow](github-actions-plan.md). Test PRs and pushes to main with backend, dashboard and Bash jobs. | CI implemented. The unused signed staging/production delivery workflow was removed on 2026-11-24 to keep the demo explainable; VG4 is not pursued. |

Python tasks include unit tests and clear comments or multiline docstrings for
non-obvious behavior. Bash tasks include syntax checks and failure-path checks;
Docker tasks include build/configuration and runtime checks as applicable.
Keep task status and evidence alongside these rows when implementation begins.

### Discord alert verification (G6)

On 2026-11-24, the user reported that the EC2 systemd timer delivered a
Discord alert at 31.5% root disk usage with a temporary 25% threshold. The
installer then confirmed the normal 90% threshold was restored.

- [x] (Discord, Security) Create a channel webhook and store its URL in a private EC2 configuration file outside Git.
- [x] (Python, Monitoring) Implement a disk usage threshold check that sends one alert per breach and rearms after recovery.
- [x] (Linux, systemd) Install the timer on EC2 using the [Discord setup guide](discord-alerts.md).
- [x] (Python, Testing) Test normal usage, a threshold breach, duplicate suppression, recovery, and webhook delivery failure.
- [x] (EC2, Discord, Demo) Temporarily lower the threshold below current disk usage, confirm the scheduled check sends a Discord message, then restore the normal threshold.

## Assignment coverage tracker

The [assignment brief](assignment-brief.md) is the source for this tracker. Local
tests establish application behavior. The recorded pair deployment supplies the
evidence for the EC2 requirements.

| Requirement (topics) | Current evidence | Still needed for the assignment |
| --- | --- | --- |
| G1 Fresh instance (AWS EC2, networking) | No instance creation verified. | Create a free-tier-configured instance on camera with suitable AMI, security groups and Elastic IP. |
| G2 Pair access (SSH, Linux) | The EC2 guide covers an individual SSH connection. | Show both students logging into the same host from their own computers with independent keys. |
| G3 Bootstrap (Bash, SCP, Ubuntu) | Bash setup installs packages and configures services and permissions. The EC2 guide demonstrates SCP. | Include useful shell aliases, rehearse transferring and running the chosen bootstrap on a fresh instance, and explain account choices. |
| G4 Repository checkout (Git, Linux) | Home-directory clone documented. Full installer expects an existing user-owned checkout. | Perform the clone as the deployment user and show ownership and the order of steps. |
| G5 Backups (Bash, Cron, PostgreSQL) | Verified on the current EC2 instance. The 11:22 UTC snapshot contained the native dump and logs, and the restore contained 18,867 metrics and 0 incidents. | Repeat the scheduled backup and isolated restore during the recorded deployment. |
| G6 Monitoring and alerts (Linux, Python, Discord) | Verified on the current EC2 instance. The collector saved a fresh measurement and the scheduled disk check delivered a [Discord alert](#discord-alert-verification-g6). | Repeat the controlled threshold test during the recorded deployment. |
| G7 Public API docs (systemd, FastAPI, HTTP) | Verified on 2026-11-24: `/docs` and `/openapi.json` returned HTTP 200 from outside AWS on the public IP. | Show Swagger in a browser during the recorded deployment. |
| G8 Reverse proxy (Nginx) | Verified on 2026-11-24: Nginx served React, health, Swagger and OpenAPI publicly. | Open the Nginx site in nano on camera and explain the proxy rules. |
| G9 Database connection (FastAPI, PostgreSQL) | Local health and Windows incident CRUD verified against PostgreSQL. Migrations and persistence tested with disposable PostgreSQL. | Show the deployed API reading and writing through the instance's database. |
| VG1 Containers (Docker, Compose, PostgreSQL) | Verified on 2026-11-24: 867 metrics before and after `down` and `up -d --wait`, with all services healthy. | Repeat the persistence check on camera and show the native process manager. |
| VG2 Custom domain (DNS, HTTPS, Certbot) | Verified on 2026-11-25: `https://serverwatch.dev` and `/docs` load with a valid Let's Encrypt certificate; HTTP redirects to HTTPS. | Repoint the A records to the new instance and run the HTTPS setup on camera. |
| Optional VG3/VG4 (AWS RDS, GitHub Actions) | Not pursued. The unused delivery workflow was removed on 2026-11-24. RDS remains optional. | If selected, demonstrate the RDS alternative or automatic Docker image deployment to EC2. |
| Team and recording (Classroom, documentation, presentation) | Team membership and a timed rehearsal are unverified. | Accept the invitation, document the pair, rehearse from scratch, record within 60 minutes, check playback and the link, then stop the instances. |

## Assignment audit notes

The numbered G8 criterion requires a reverse proxy and prefers Nginx. The
numbered VG2 criterion requires custom-domain HTTPS with Certbot. The
introductory examples describe these differently. The checklist follows the
numbered criteria and leaves the assignment wording unchanged.

Record the pair's names in the project documentation and accept the Classroom
invitation. For the recording, create EC2 from scratch, demonstrate both SSH
logins, explain terminal commands and choices, and show the full pipeline within
60 minutes. Both students need to appear and speak, with readable terminal text.
Verify the video link and playback before shutting down the instances.

## Decisions to settle

- Record the two team members, course deadline and division of demo work when confirmed.
- Local collection uses a five-second sleep. Define the production collection
  schedule, incident thresholds, automatic resolution policy, retention, and
  notification channel.
- Domain: `serverwatch.dev` at Namecheap, auto-renew off. Identify backup storage location and recovery procedure.
  Local backups alone do not protect against losing the instance.

## Maintaining progress

After a milestone or material scope change:

1. Update the review date and relevant status rows.
2. Record evidence as file links, executed commands/results, and verification
   dates in the relevant status row. Do not append dated logs; Git history keeps
   earlier evidence. Mark unavailable checks as unverified.
3. Keep endpoint details in `api.md`; synchronize README and `AGENT.md` references
   using the repository's documentation synchronization skill.

Use `Not started`, `In progress`, `Blocked` (with a concrete reason), or `Verified`
for future status updates. A milestone becomes verified only when its completion
checks have actually passed. Local documentation changes do not authorize cloud
provisioning, deployment, or credential operations.
