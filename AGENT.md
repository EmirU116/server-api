# ServerWatch — AI Agent Instructions

> **Applies to:** All AI coding agents and developers contributing to ServerWatch.
> **Project:** Server Monitoring & Incident Management Platform.
> **Status:** This file describes intended architecture and working conventions, **not proof that each component already exists**.

## 1. Mission

Build a small, understandable, production-style application that monitors an Ubuntu EC2 instance, stores health metrics, detects incidents, and provides an API for viewing and managing them.

**Primary goal:** Satisfy the course's G/VG deployment requirements while keeping the code secure, maintainable, easy to explain, and useful in a portfolio.

**Preferred stack:** Python / FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, Docker Compose, Ubuntu EC2, Bash, Cron, Nginx, Certbot, GitHub Actions. A React frontend is an optional later extension.

Avoid introducing Kubernetes, microservices, RDS, Terraform, message brokers, or additional cloud services unless explicitly requested and justified. RDS is optional bonus work, not a prerequisite.

## 2. First actions for every task

1. Read `README.md`, this file, and `docs/FOLDER_STRUCTURE.md` (if they exist).
2. Inspect the relevant files and actual repository layout; **do not assume** proposed paths, endpoints, tables, or services have been implemented.
3. Identify the smallest change that satisfies the request. Describe planned file additions or moves when the change is substantial.
4. Preserve the existing architecture and naming conventions unless there is a compelling reason to change them.
5. After changes, run relevant tests, formatting, linting, or configuration validation that the project actually supports.
6. Report what changed, what was verified, and any remaining risks or manual steps.

When requirements are unclear, choose a conservative, reversible implementation and make assumptions explicit. Do not silently invent product requirements.

### Documentation references

Read the documents relevant to the task before editing code. These references
describe requirements and conventions; verify implementation status separately.

| Document | When to read it |
|---|---|
| [Project overview](README.md) | Starting work and finding project documentation. |
| [Folder structure](docs/FOLDER_STRUCTURE.md) | Creating, moving, or organizing files and modules. |
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

If the existing repo uses a slightly different structure, follow the established structure unless asked to refactor it.

## 4. Intended architecture and traffic

**Public request flow:**

```text
Browser/client -> HTTPS :443 -> Nginx on EC2 -> FastAPI/Uvicorn -> PostgreSQL
```

**Local monitoring flow:**

```text
Cron -> Bash host metrics collector -> authenticated local FastAPI endpoint
     -> PostgreSQL -> incident detection -> Discord notification when needed
```

**Deployment flow (optional bonus):**

```text
GitHub Actions -> tests/build -> versioned Docker image -> approved EC2 deployment
```

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
- **Python:** Use type hints, small functions, explicit error handling and descriptive `snake_case` filenames. Prefer dependency injection for database sessions and external services.
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
- Working FastAPI service, demonstrated with systemd or supervisor.
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
