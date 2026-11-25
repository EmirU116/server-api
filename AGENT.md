# ServerWatch — AI Agent Instructions

> **Applies to:** All AI coding agents and developers contributing to ServerWatch.
> **Project:** Server Monitoring & Incident Management Platform.
> **Status:** This file describes intended architecture and working conventions, **not proof that each component already exists**.

## 1. Mission

Build a small, understandable, production-style application that monitors an Ubuntu EC2 instance, stores health metrics, detects incidents, and provides an API for viewing and managing them.

**Primary goal:** Satisfy the course's G/VG deployment requirements while keeping the code secure, maintainable, easy to explain, and useful in a portfolio.

**Application languages:** Use Python only for backend/API application code and React with TypeScript for the frontend. Bash remains available for host automation.

**Preferred stack:** Python / FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, Docker Compose, Ubuntu EC2, Bash, Cron, Nginx, Certbot, GitHub Actions. A React frontend is an optional later extension.

Avoid introducing Kubernetes, microservices, RDS, Terraform, message brokers, or additional cloud services unless explicitly requested and justified. RDS is optional bonus work, not a prerequisite.

## 2. First actions for every task

1. Read `README.md` and this file.
2. Inspect the relevant files and actual repository layout; **do not assume** proposed paths, endpoints, tables, or services have been implemented.
3. Identify the smallest change that satisfies the request. Describe planned file additions or moves when the change is substantial.
4. Preserve the existing architecture and naming conventions unless there is a compelling reason to change them.
5. After changes, run relevant tests, formatting, linting, or configuration validation that the project actually supports.
6. Use supported APIs. Check deprecation claims against the official documentation for the project's supported versions and replace confirmed deprecated calls with supported equivalents. Python's `contextlib.contextmanager` and `contextlib.asynccontextmanager` are supported. Use FastAPI's `lifespan=` for application lifecycle hooks.
7. Report what changed, what was verified, and any remaining risks or manual steps.

When requirements are unclear, choose a conservative, reversible implementation and make assumptions explicit. Do not silently invent product requirements.

Use root `setup.sh` and `verify.sh` as the EC2 deployment entry points.
Reuse the component installers for optional Discord, Ubuntu accounts, and
Compose stages. See the [EC2 setup guide](docs/ec2-manual-setup.md).

### Documentation references

Read the documents relevant to the task before editing code. These references
describe requirements and conventions; verify implementation status separately.

| Document | When to read it |
|---|---|
| [Local stack launcher](docs/local-development.md) | Starting the existing Windows database, FastAPI, and React together from Git Bash/WSL; launcher checks, process cleanup, and Windows-only limitations. |
| [Local PostgreSQL](docs/local-postgresql.md) | Database settings, Windows startup, and connectivity checks. |
| [Project overview](README.md) | Starting work and finding project documentation. |
| [Git and GitHub Actions workflow](docs/github-actions-plan.md) | Branches, agent worktrees, human review, and the PR checks. |
| [Continuous deployment](docs/continuous-deployment.md) | The optional VG4 deploy workflow: GHCR images per commit, the restricted GitHub SSH key, repository secrets, and enabling or disabling automatic deploys. |
| [Course assignment](docs/assignment-brief.md) | Checking the supplied G/VG criteria, team responsibilities, optional bonuses, and recording rules. |
| [Project plan and progress](docs/project-plan.md) | Checking the current stage, choosing the next milestone, and tracking assignment completion. Update it with evidence after milestone completion or material scope changes. |
| [Frontend development](docs/frontend.md) | Working on the React/TypeScript UI, demo/live data separation, API client, local development proxy, or frontend checks. |
| [Ubuntu host monitoring](docs/ubuntu-monitoring.md) | Installing native Ubuntu PostgreSQL, migrations, API/collector systemd services, or verifying fresh persisted measurements. |
| [Discord alerts](docs/discord-alerts.md) | Configuring the webhook privately and reproducing the verified G6 alert during the demo. |
| [Docker deployment](docs/docker-deployment.md) | Building and running Compose, host-owned Compose settings, migrating existing volumes with separate migration and runtime roles, and exposing the stack through host Nginx. |
| [Ubuntu accounts and permissions](docs/ubuntu-accounts.md) | Creating junior and senior accounts, verifying ACLs, and keeping workspace access separate from service credentials. |
| [Presentation guide](docs/presentation-guide.md) | Preparing or changing the recorded demo: order, timing, commands, explanations and talking points. Update it when a demo-relevant feature or command changes. |
| [Presentation notebook](docs/presentation-guide.ipynb) | The solo version of the presentation guide as a Jupyter notebook, with a rehearsal timer. Keep its steps in sync with the guide. |
| [EC2 manual setup and deployment rehearsal](docs/ec2-manual-setup.md) | Creating a fresh instance, running full setup, testing the public IP, demonstrating native Cron backups and restore, and the custom domain with Certbot HTTPS (VG2). |
| [API specification](docs/api.md) | Implementing or changing health, metrics, server information, incident CRUD, validation, error handling, API tests, or code comments. The current contract targets one monitored server. |
| [Secrets management](docs/SECRETS_MANAGEMENT.md) | Handling credentials, authentication configuration, containers, monitoring, or deployment; use its storage and approval rules. |

Use `docs/api.md` for the proposed HTTP paths, methods, payloads, and authentication
contract. Deployment snippets in other guides may be illustrative or older; do
not copy a conflicting route or header into an implementation. Report unresolved
conflicts rather than silently changing security requirements. The broader
capabilities in section 5 remain architectural goals, not additional endpoints
required by the current API contract.

### Keep agent instructions aligned with documentation

Apply the repository skill
[sync-agent-docs](.agents/skills/sync-agent-docs/SKILL.md) whenever a task adds,
renames, moves, or removes a documentation file, or materially changes documented
requirements. Update this reference table and any affected instructions in the
same task, without waiting for a separate user request. Include relevant project
guides outside `docs/`, such as `README.md`; exclude placeholders and generated
documentation artifacts.

A material change affects API contracts, architecture, security rules, folder
ownership, development or testing requirements, deployment procedures, or demo
constraints. Typo fixes and formatting-only changes do not require an `AGENT.md`
edit unless they fix a reference. Keep detailed requirements in their owning
documents and link to them here instead of copying whole sections.

This is an agent workflow rule, not a background file watcher. Agents following
this file must perform the synchronization during relevant tasks.

### Repository maintenance skills

- When the user says `code-review` or `code-review <scope>`, apply
  [code-review](.agents/skills/code-review/SKILL.md). With no scope, review the
  current project.

- When implementing, editing, or reviewing an API operation, apply [explain-api-errors](.agents/skills/explain-api-errors/SKILL.md). Every handled failure across every method and status must explain its known cause safely. Test the public response.
- Use a scoped task branch for agent changes and a separate worktree for concurrent contributors. Agents run the same checks as humans and report test evidence. The human maintains publication and merge authority. See the [CI workflow guide](docs/github-actions-plan.md).
- Use [maintain-gitkeep](.agents/skills/maintain-gitkeep/SKILL.md) when changing which files preserve a project directory in Git.
- Use [reuse-python-code](.agents/skills/reuse-python-code/SKILL.md) when Python callers duplicate behavior. Shared backend API helpers belong in `backend/app/reusable.py` and have direct tests.

### Implementation rules

Track progress only in [the project plan](docs/project-plan.md); keep status out
of this file. These rules apply to the implemented code:

- **App wiring:** `backend/app/main.py:create_app` puts settings, the database,
  services and role tokens on `app.state`. Settings and shared errors live in
  `backend/app/core/`. Use the README's startup commands and run
  `python -m pytest backend/tests tests -q` and the Ruff checks from the root.
- **Schema:** Alembic migrations only. Never create tables or apply migrations
  at application startup.
- **Server ID:** health requires a positive numeric `server_id` (invalid → 400,
  unregistered → 404, missing → 422); `GET /server` accepts it optionally.
  Prefer readable `int()` conversion over regex or arbitrary limits. See
  [the API contract](docs/api.md).
- **Health:** probes run concurrently with a 150 ms timeout (target p95 below
  200 ms), stay nonblocking and cancellation-aware, and report unconfigured or
  failed dependencies as down in a structured 503.
- **Host identity:** `GET /server` describes the native host. Never present
  container metadata as host identity; Compose mounts a host identity file.
- **Roles:** reader (GET), collector (POST metrics) and admin (incident writes)
  tokens are separate, each set by environment or `_FILE`, and must differ.
  Roles do not inherit permissions; a wrong role returns 403.
- **Incidents:** `IncidentsService` scopes records to the configured server and
  locks rows for updates and deletes. Editing a resolved incident keeps its
  resolution time; reopening clears it. Planned incidents have no occurrence
  time. Trigger thresholds support manual review only; nothing opens incidents
  automatically.
- **Collector:** `scripts/monitoring/collect_local.py` measures with `psutil`
  and POSTs to the local API every five seconds with the collector token. On
  Ubuntu it runs under systemd.
- **Ubuntu setup:** `infrastructure/bootstrap/setup_ubuntu_monitoring.sh` keeps
  managed configuration in `~/.config/serverwatch-monitoring`, preserves
  existing secrets and data, never imports the project `.env`, and restarts
  services when rerun. Do not run it on a workstation or server without
  authorization. See [the Ubuntu guide](docs/ubuntu-monitoring.md).
- **Local launcher:** `scripts/setup/start_local.sh` uses Windows Python and
  Node through PowerShell, even from WSL. It reuses the private `.env` (never
  source or print it), installs nothing, applies no migrations, and stops only
  the processes it started. See [the launcher guide](docs/local-development.md).
- **Frontend:** starts in labeled demo mode; keep demo data separate from API
  responses. Tokens live only in React memory, never in build variables or
  browser storage, and live tokens require HTTPS or localhost. The client uses
  same-origin `/api/v1` (a Vite proxy in development). Never send the collector
  token to the frontend. See [the frontend guide](docs/frontend.md).

## 3. Canonical folder ownership

Place files by **responsibility**, not solely by extension.

| Location | Belongs here | Does **not** belong here |
|---|---|---|
| `backend/app/api/` | FastAPI routers, request handling, dependencies | Complex business logic, host administration scripts |
| `backend/app/models/` | SQLAlchemy entities and relationships | HTTP routes, UI |
| `backend/app/schemas/` | Pydantic request/response contracts | Raw database access |
| `backend/app/services/` | Monitoring, incident and notification domain logic | Nginx config, Cron schedules |
| `backend/app/repositories/` | Database queries/persistence, if this layer is used | HTTP route definitions |
| `backend/app/core/` | Backend configuration, security and shared app utilities | Host provisioning |
| `backend/migrations/` or `backend/alembic/` | Versioned DB schema migrations; use the established choice | Runtime data or backups |
| `backend/tests/` | Backend unit/integration tests | Production secrets or resources |
| `frontend/` | Optional UI, assets and frontend API client | Database credentials, backend business logic |
| `infrastructure/aws/` | AWS-related definitions and instructions | Application endpoints |
| `infrastructure/nginx/` | Nginx site templates/config | Bash app logic |
| `infrastructure/systemd/` | systemd units for native process-manager demo or host services | Python route code |
| `infrastructure/cron/` | Cron schedule templates | Executable monitoring implementation |
| `infrastructure/bootstrap/` | First-boot EC2 setup/provisioning scripts | Routine application domain logic |
| `scripts/deployment/` | Deployment, rollback and release helpers | Source modules |
| `scripts/monitoring/` | Host metric collectors and operational checks | FastAPI routers |
| `scripts/backup/` | Backup/restore/retention scripts | Generated backup files |
| `scripts/verification/` | Deployment smoke checks, diagnostics | Production app code |
| `tests/` | Cross-component/end-to-end tests, where needed | Duplicates of backend-only tests |
| `.github/workflows/` | CI and deployment workflows | App secrets, application source |
| `docs/` | Architecture, operations, security, demo instructions | Active configs, executable scripts |
| Repository root | `README.md`, `compose.yaml`, `.env.example`, `.gitignore`, agent instructions | Miscellaneous temporary code and unrelated files |

**Placement rule:** Store a file in exactly one authoritative location. For example, `scripts/monitoring/collect_metrics.sh` performs the work, while `infrastructure/cron/monitoring.cron` specifies its schedule. Do not maintain duplicate implementations.

When placing a new file, ask in order: is it application code (`backend/`,
`frontend/`)? Host or cloud configuration (`infrastructure/`)? An executable
operational helper (`scripts/`, or `infrastructure/bootstrap/` for first-boot
setup)? A test (the component's `tests/`, or root `tests/` for scripts and
cross-component checks)? An explanation (`docs/`)? Create a folder only when
several related files share its responsibility.

If the existing repo uses a slightly different structure, follow the established structure unless asked to refactor it.

## 4. Intended architecture and traffic

**Public request flow:**

```text
Browser/client -> HTTPS :443 -> Nginx on EC2 -> FastAPI/Uvicorn -> PostgreSQL
```

**Local monitoring flow:**

```text
systemd -> Python host metrics collector -> authenticated local FastAPI endpoint -> PostgreSQL
systemd timer -> disk threshold check -> Discord webhook
```

**Deployment flow:** manual — clone on EC2, then run `setup.sh` (native) or
`compose_host.sh start` (Compose). Automated GitHub Actions deployment is an
unimplemented optional bonus.

Architecture constraints:
- Run FastAPI and PostgreSQL in separate Docker Compose services for VG.
- Use service-name DNS such as `db:5432` for API-to-database traffic inside the Compose network.
- Do **not** publish PostgreSQL's port publicly.
- Bind the API host port to loopback (for host-based Nginx) or keep it on a private Docker network (for containerized Nginx).
- Use Nginx as the public-facing reverse proxy; terminate TLS on port 443 and redirect HTTP where appropriate.
- Keep PostgreSQL data in persistent volumes and apply schema changes through migrations.
- Use systemd to demonstrate a native Uvicorn deployment as required by the assignment, then stop it before using the final containerized deployment on the same port. Do not unintentionally run conflicting services.
- Do not assume that a frontend is required for VG. Prioritize deployable backend infrastructure first.

## 5. Application behavior

Minimum planned capabilities (implement incrementally; check existing routes before adding any):

- Register/list monitored servers.
- Accept authenticated metric submissions (CPU, memory, disk utilization, timestamps).
- Retrieve current and historical metrics.
- Create/list/get/update incidents, including severity and status.
- Detect threshold breaches and avoid duplicate open incidents for the same condition.
- Send alert notifications safely; handle notification failures without corrupting stored data.
- Provide a lightweight liveness endpoint and a readiness endpoint that verifies dependencies.

Keep HTTP validation and serialization in API/schema modules. Put domain decisions in services and persistence in the established DB layer. Avoid expensive blocking work inside request handlers; make notification delivery reliable enough for the prototype and clearly document limitations.

## 6. Coding and naming conventions

- **Comments:** Add clear comments to explain intent, non-obvious logic, assumptions and important decisions so contributors can understand the code. Keep comments accurate and avoid restating obvious operations.
- **Readable formatting:** Use multiline formatting for long function calls, conditions, collections and commands when it improves readability. Separate logical steps with blank lines and avoid dense one-liners; follow the project's formatter and language conventions.
- **Python:** Prioritize simple, Pythonic code that is easy to read and explain. Prefer standard built-ins, clear names, and straightforward control flow. Avoid clever one-liners, unnecessary regex, and abstractions when a simpler approach meets the requirements. Keep required validation and error handling. Use type hints, small functions, and descriptive `snake_case` filenames. Prefer dependency injection for database sessions and external services.
- **API errors:** Explain expected failures with public, application-controlled messages. Preserve status codes, role challenges and structured health reports. Cover the reason in response tests.
- **Pydantic:** Separate input and output schemas; never expose password hashes or internal secrets.
- **Database:** Use migrations, parameterized queries/ORM, explicit relationships and constraints, and UTC timestamps. Avoid unreviewed destructive migrations.
- **Bash:** Start scripts with `#!/usr/bin/env bash`; use `set -euo pipefail` where appropriate; quote variables; check prerequisites; avoid relying on the current working directory; make provisioning idempotent where practical.
- **Docker:** Use reproducible images, `.dockerignore`, health checks where relevant, restart policies and pinned image versions where feasible. No production `--reload`.
- **Naming:** `snake_case.py`, `test_*.py`, `snake_case.sh`, descriptive `.md` names; React components in `PascalCase` if a frontend is added.
- **Dependencies:** Add only when justified. Update dependency manifests and documentation together.
- **Simplicity:** Do not create empty layers, unnecessary abstraction or extra directories just for appearances.

## 7. Security and secrets — non-negotiable

- Never commit or print `.env`, real credentials, Discord webhook URLs, SSH private keys, TLS private keys, tokens or database dumps.
- Commit `.env.example` with **placeholder** values only.
- Require appropriate authentication for metric ingestion and state-changing API endpoints; do not publish admin actions anonymously.
- Follow least privilege for EC2 IAM, GitHub Actions, Linux users, container processes and database accounts.
- Restrict inbound SSH (`22`) to authorized source IPs where practical; expose only necessary HTTP (`80`) and HTTPS (`443`) ports.
- Never expose PostgreSQL (`5432`) to the public internet; do not use `chmod 777` as a workaround.
- Keep backups and credentials outside tracked source directories. Restrict their filesystem permissions.
- Do not log sensitive HTTP headers, passwords, tokens or webhook addresses.
- Confirm before applying changes that affect live cloud resources, access controls, billing or persistent data.

## 8. Safety and approval gates for AI agents

**Allowed without additional approval (within the requested task):**
- Read files and propose a plan.
- Modify local application code, tests, documentation and non-sensitive config templates.
- Run local linting, formatting and tests that do not modify external resources.
- Create non-destructive verification scripts.

**Ask for explicit approval before:**
- Deploying to AWS or changing live EC2 resources, security groups, DNS or certificates.
- Pushing code, merging branches, publishing images, or triggering production CI/CD.
- Executing destructive commands (e.g., dropping DB tables, deleting volumes, force-pushing, recursively removing data).
- Creating/rotating SSH keys, modifying users or permissions on remote systems, or changing secret material.
- Running commands that could incur cloud charges or affect shared services.

Never claim that deployment, tests, backups, or security checks succeeded unless actually verified.

## 9. Testing and validation expectations

Choose commands based on files/tooling found in the repository; don't assume the following are installed.

- **Backend:** Run relevant `pytest` tests; cover API success/failure, validation, DB operations and incident deduplication.
- **Containers:** `docker compose config` must parse cleanly; verify service health with `docker compose ps` and logs as needed.
- **Nginx:** Test active configuration with `sudo nginx -t` before reloading it.
- **Bash:** Check `bash -n path/to/script.sh` and, when available, ShellCheck; test failure paths.
- **Database:** Test migrations against an isolated database. Verify that a backup can actually be restored, not merely created.
- **Deployment:** Run health checks and ensure API/database connectivity and persistence survive service/container restarts.
- **HTTPS:** Verify certificate and redirect behavior; test renewal where feasible.
- **CI/CD:** Validate workflows and use least-privilege credentials; do not deploy untested changes.

Where testing is unavailable, state precisely what remains unverified.

## 10. Course requirements and demonstration constraints

**The recorded pair demo has a hard 60-minute limit and the EC2 instance must be created from scratch during recording.** Prepare scripts, infrastructure templates, application code and documentation beforehand; do not substitute a pre-existing EC2 instance during the demo.

### Required G items

- New AWS EC2 instance with appropriate AMI, security groups and Elastic IP.
- Independent SSH key access for both students.
- Bash bootstrap script transferred via SCP and executed on the instance.
- Clone the repository on the instance with suitable ownership/permissions.
- Scheduled PostgreSQL/log backups using Cron; document that local-only backups are not disaster recovery.
- Scheduled health monitoring and Discord/email alerts.
- Working FastAPI service, demonstrated with systemd or supervisor and publicly accessible Swagger at `/docs`. The current production profile disables Swagger and its schema. Track the deployment change under G7 in the project plan.
- Nginx reverse proxy.
- PostgreSQL connected to FastAPI.

### Required VG items

- A suitable Dockerfile and Compose deployment of **both FastAPI and containerized PostgreSQL**.
- A custom domain and working HTTPS configuration using Certbot.

### Optional VG-strengthening items

- GitHub Actions CI/CD deployment.
- RDS instead of local/container DB only if intentionally pursuing this optional bonus (discuss its effect on the expected Docker/PostgreSQL demonstration).
- Frontend/dashboard and extra monitoring features after core requirements are stable.

### Demo-first guidance

- Both students must work from their own machines, speak and explain technical choices.
- Practice the deployment end-to-end from a blank instance.
- Prefer understandable commands and visible configuration edits over opaque one-line setup commands.
- Keep `docs/demo-checklist.md` (if created) aligned with the actual pipeline.
- Plan DNS ahead, but do not assume a preallocated Elastic IP is permitted unless the instructor confirms.
- After recording, stop/terminate unused resources and release unneeded billable assets following course instructions.

## 11. Definition of done and response format

A task is complete when the code/configuration follows folder ownership, the appropriate tests or validations have been performed, documentation is updated when necessary, and no secrets or unsafe infrastructure changes were introduced.

At the end of every implementation task, give a concise report:

1. **Changed:** Files created/modified and why.
2. **Verified:** Commands/tests run and their outcomes.
3. **Not verified:** Any missing tests or blocked checks.
4. **Next:** A single recommended next step if useful.

**Operating principle:** Favor explainable, secure, reversible changes over clever automation. The two students must understand and be able to demonstrate the implementation themselves.
