# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**`AGENT.md` is the canonical agent guide** (architecture, folder ownership, security rules, approval gates, course/demo constraints, end-of-task report format). Read it before substantial work; this file only summarizes and does not override it. `docs/api.md` is the authoritative HTTP contract — deployment guides may show older routes/headers; report conflicts instead of copying them.

## Project

ServerWatch: FastAPI + PostgreSQL monitoring/incident API with a React/TypeScript dashboard, deployed to a single Ubuntu EC2 host (native systemd + Nginx for the G criteria, Docker Compose + Certbot HTTPS for VG). It is a course assignment (`docs/assignment-brief.md`); progress and remaining milestones are tracked in `docs/project-plan.md` — update it with evidence when a milestone completes. Python only for backend code, Bash for host automation. Avoid adding Kubernetes, Terraform, brokers, or extra cloud services.

## Commands

Backend (repo root, Python 3.11+, venv active — `.venv` exists for WSL):

```bash
python -m pip install -r backend/requirements-dev.txt
python -m uvicorn app.main:create_app --factory --app-dir backend --env-file .env --reload --host 127.0.0.1 --port 8000
python -m pytest backend/tests tests -q -ra            # full suite (what CI runs)
python -m pytest backend/tests/test_health.py -q -k invalid   # single file / filter
python -m ruff check backend/app backend/tests
python -m ruff format --check backend/app backend/tests
python backend/migrate.py --env-file .env              # alembic upgrade head (--sql to print only)
```

- `*_postgresql.py` and migration tests spin up a private throwaway cluster via `initdb`/`pg_ctl`; they are **skipped** if PostgreSQL server binaries aren't found, and must run as non-root.
- Tests never load `.env`; `backend/tests/conftest.py` strips all `SERVERWATCH_*` env vars.
- `backend/tests/` = app tests; root `tests/` = tests of Bash/Python automation scripts (launcher, collector, setup, Compose).

Frontend (`frontend/`, Node 22.12+): `npm ci --include=optional`, `npm run dev`, `npm run typecheck`, `npm test` (vitest; single file: `npx vitest run tests/api.test.ts`), `npm run build`, `npm run format:check`.

Other checks: `bash -n <script>.sh` (CI parses every tracked `.sh`), `docker compose config`.

Local full stack on the user's Windows machine (from Git Bash/WSL): `bash scripts/setup/start_local.sh` — uses Windows Python/Node via PowerShell, not WSL tooling.

EC2 entry points: `bash setup.sh PUBLIC_IP` and `bash verify.sh PUBLIC_IP` (`SERVERWATCH_DOMAIN=serverwatch.dev` adds Certbot HTTPS via `infrastructure/bootstrap/setup_https.sh`); Compose via `scripts/deployment/compose_host.sh start|collect`. Optional CD (VG4): `.github/workflows/deploy.yml` runs after green CI on `main`, pushes GHCR images tagged by SHA, and SSHes in with a forced-command key to `scripts/deployment/deploy_image.sh` (`docs/continuous-deployment.md`). These modify hosts — never run them on a workstation or live server without explicit approval.

## Architecture

- **App factory**: `backend/app/main.py:create_app(settings)` wires everything onto `app.state` (Database, services, role tokens) — no globals, so tests build isolated apps with explicit `Settings`. Lifecycle uses `lifespan=`.
- **Layers**: `api/` routers (HTTP validation only) → `services/` (domain logic, transactions, row locks) → `models/` (SQLAlchemy); `schemas/` holds separate Pydantic input/output models. Shared API helpers go in `backend/app/reusable.py` with direct tests. Settings in `core/config.py`, tokens in `core/security.py`, structured error handlers in `core/errors.py`.
- **Auth model**: three distinct bearer tokens — reader (GETs), collector (POST metrics), admin (incident writes). Roles do not inherit; startup fails if any two configured tokens match. Every secret accepts a `*_FILE` variant that takes precedence. Health is public.
- **Single server scope**: all data is scoped to `SERVERWATCH_SERVER_ID` (default 1). Invalid IDs → 400, unknown → 404, missing required → 422, failed dependency → structured 503. Health probes run concurrently with a 150 ms timeout.
- **Schema**: Alembic only (`backend/alembic/versions/000N_*.py`); never auto-create tables or migrate at startup.
- **Data flow**: host collector (`scripts/monitoring/collect_local.py`, psutil, 5 s loop; systemd on Ubuntu) → `POST /api/v1/metrics` → PostgreSQL ← dashboard polls `GET` every 5 s with a reader token. Frontend uses same-origin `/api/v1` (Vite proxy in dev, Nginx in prod), starts in labeled demo mode (`services/demo.ts`) kept separate from live data; tokens live only in memory.
- **Compose** (`compose.yaml`): `db` (postgres:17, internal network only) → one-shot `migrate` (separate migrator role, then grants runtime role) → `api` → `web` (Nginx image, bound to loopback; host Nginx fronts it). Secrets come from files in `${SERVERWATCH_COMPOSE_SECRETS:-./secrets}`.
- **Host automation**: `setup.sh` is the only supported entry point; it orchestrates `infrastructure/bootstrap/*` (packages/PostgreSQL/services/Cron, then web/Nginx, Discord timer) and user provisioning. Implementations live in `scripts/`, schedules/units in `infrastructure/` — one authoritative location per file. The native deployment is manual; only the Compose stack can be deployed automatically (optional, gated by the `SERVERWATCH_DEPLOY_ENABLED` repo variable).
- **Shared stdlib helpers** (used by scripts that run with system Python before `.venv` exists): `backend/app/host_identity.py` (host identity for the API and Compose) and `scripts/setup/private_files.py` (create-once 600/700 credential files).

## Repo-specific rules

- Every handled API failure must return a safe, explanatory public message, and tests must assert it (`.agents/skills/explain-api-errors`).
- When adding/renaming/removing docs or materially changing requirements, update the docs table in `AGENT.md` in the same task (`.agents/skills/sync-agent-docs`).
- Other repo skills under `.agents/skills/`: `code-review`, `maintain-gitkeep`, `reuse-python-code`, `secure-repo-secrets`.
- Never read out, print, or commit `.env`, tokens, webhook URLs, or the `secrets/` contents.
- Prefer simple, explainable code with comments on intent — two students must be able to demo and explain it.
