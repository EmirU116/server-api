# Folder Structure Rules & Conventions

## 1. Purpose

This document defines how files, scripts, configurations, and modules should be organized within the project.

**Core rule: Every folder must have a clear responsibility, and every file should be placed according to its purpose.**

Avoid mixing application logic, infrastructure configuration, documentation, and tests in the same directory.

## 2. General project structure

```text
project/
├── backend/             # Backend application code
├── frontend/            # Frontend application code
├── infrastructure/      # Infrastructure and server setup
├── scripts/             # Development and maintenance scripts
├── tests/               # Cross-component and end-to-end tests
├── docs/                # Project documentation
├── .github/             # GitHub configuration and CI/CD
├── compose.yaml         # Docker Compose configuration
├── .env.example         # Environment variable examples
├── .gitignore           # Git exclusions
└── README.md            # Project overview
```

Only create folders when they have a meaningful responsibility. Empty folders should not be created unnecessarily.

---

## 3. Folder responsibility rules

### `/backend/` — Backend application

**Contains:**
- Backend application source code.
- REST API endpoints.
- Database models and connections.
- Request and response schemas.
- Business logic and services.
- Backend-specific dependencies and configuration.
- Database migrations.
- Backend-specific tests.
- Backend Dockerfile.

**Does not contain:**
- Frontend UI components.
- Linux server configuration scripts.
- Nginx configuration.
- GitHub Actions workflows.
- Database backups or runtime logs.

Recommended internal organization:

```text
backend/
├── app/
│   ├── api/          # API routes and controllers
│   ├── models/       # Database models
│   ├── schemas/      # Data validation and contracts
│   ├── services/     # Business logic
│   ├── repositories/ # Database queries and persistence
│   ├── core/         # Shared application configuration
│   └── main.py       # Application entry point
├── migrations/       # Database migration files
├── tests/            # Backend tests
├── Dockerfile
└── requirements.txt
```

### `/frontend/` — User interface

**Contains:**
- HTML, CSS, JavaScript or TypeScript.
- React components and pages.
- UI layouts and styles.
- Frontend API clients.
- Images, icons and static assets.
- Frontend-specific configuration and tests.

**Does not contain:**
- Backend business logic.
- SQL database models or migrations.
- Linux system scripts.
- Server-side secrets.
- PostgreSQL database files.

Recommended organization:

```text
frontend/
├── src/
│   ├── components/   # Reusable UI components
│   ├── pages/        # Application pages
│   ├── services/     # Frontend API client
│   ├── hooks/        # Reusable React hooks
│   ├── styles/       # CSS and styling
│   └── assets/       # Imported images and icons
├── public/           # Static public assets
├── tests/            # Frontend tests
├── package.json
└── Dockerfile
```

### `/infrastructure/` — Infrastructure configuration

**Contains:**
- Cloud infrastructure definitions.
- EC2 provisioning and bootstrap scripts.
- Linux server setup configuration.
- Nginx reverse proxy configurations.
- systemd service definitions.
- Cron configuration.
- Infrastructure-specific automation.
- Infrastructure as Code templates, if used.

**Does not contain:**
- FastAPI route handlers.
- Frontend components.
- Application business logic.
- Runtime database data.
- Generated logs or database backups.

Recommended organization:

```text
infrastructure/
├── aws/         # AWS-specific infrastructure definitions
├── nginx/       # Nginx configuration files
├── systemd/     # Linux service definitions
├── cron/        # Cron schedule templates
└── bootstrap/   # Initial server setup scripts
```

**Rule:** Infrastructure defines how the environment is configured. Application code defines what the application does.

### `/scripts/` — Automation and utility scripts

**Contains:**
- Bash and Python utility scripts.
- Deployment helpers.
- Database backup and restoration scripts.
- Server health-check scripts.
- Maintenance scripts.
- Development environment setup scripts.
- Verification and troubleshooting utilities.

**Does not contain:**
- FastAPI endpoints.
- Application business logic that belongs in backend services.
- React components.
- Configuration files unrelated to the scripts.
- Generated backup archives or log files.

Recommended organization:

```text
scripts/
├── deployment/      # Deployment and rollback scripts
├── monitoring/      # Metric collection and host checks
├── backup/          # Database backup and restore
├── setup/           # Developer environment setup
└── verification/    # Validation and smoke-test scripts
```

**Rule:** Scripts perform tasks. Infrastructure files define configuration.

For example:
- `scripts/monitoring/collect_metrics.sh` collects CPU and memory usage.
- `infrastructure/cron/monitoring.cron` defines when that script executes.

Avoid placing the same script in both folders.

### `/tests/` — Cross-component testing

**Contains:**
- Integration tests involving multiple components.
- End-to-end tests.
- Deployment smoke tests.
- Test fixtures and mock data.

**Does not contain:**
- Production application code.
- Production credentials.
- Database backups.
- Unrelated infrastructure configuration.

**Rule:** Tests specific to one application component should normally remain near that component, such as `backend/tests/`. Root-level tests should focus on integration across components.

### `/docs/` — Documentation

**Contains:**
- Architecture descriptions and diagrams.
- API specifications.
- Setup guides.
- Deployment instructions.
- Development guidelines.
- Troubleshooting documentation.
- Project decisions and conventions.

**Does not contain:**
- Executable application source code.
- Actual private credentials.
- Runtime databases.
- Generated logs.
- Deployable infrastructure configurations.

Example:

```text
docs/
├── architecture.md
├── api.md
├── development.md
├── deployment.md
├── folder-structure.md
└── troubleshooting.md
```

Documentation may contain code snippets and example commands, but the actual executable implementation should live in its designated source folder.

### `/.github/` — GitHub automation

**Contains:**
- GitHub Actions workflows.
- Pull request templates.
- Issue templates.
- GitHub-specific configuration.

**Does not contain:**
- Application source files.
- Linux scripts unrelated to GitHub automation.
- Database files.
- Production secrets.

Example:

```text
.github/
├── workflows/
│   ├── ci.yml
│   └── deploy.yml
├── ISSUE_TEMPLATE/
└── pull_request_template.md
```

---

## 4. Root directory conventions

The repository root should contain only files required to understand, configure, or operate the entire project.

| File | Responsibility |
|---|---|
| `README.md` | Main project overview and getting started |
| `.gitignore` | Files excluded from version control |
| `.env.example` | Example environment variables without real secrets |
| `compose.yaml` | Multi-container application configuration |
| `compose.override.yaml` | Optional local development overrides |
| `AGENTS.md` | Repository-wide AI agent instructions |
| `LICENSE` | Project license, when applicable |

Avoid placing large application modules, miscellaneous Bash scripts, or unrelated temporary files directly in the root.

---

## 5. Naming conventions

Use consistent names that clearly indicate a file's purpose.

| File type | Convention | Example |
|---|---|---|
| Python modules | `snake_case.py` | `incident_service.py` |
| Python tests | `test_*.py` | `test_metrics.py` |
| Bash scripts | `snake_case.sh` | `backup_database.sh` |
| React components | `PascalCase.tsx` | `ServerStatus.tsx` |
| React hooks | `useCamelCase.ts` | `useMetrics.ts` |
| Documentation | `kebab-case.md` | `deployment-guide.md` |
| Environment examples | `.env.example` | `.env.example` |
| Docker configuration | Standard Docker filenames | `Dockerfile`, `compose.yaml` |
| GitHub workflows | Descriptive YAML filenames | `deploy.yml` |

Prefer descriptive names over generic names like `helpers.py`, `stuff.sh`, `new_file.py`, or `final_v2.py`.

---

## 6. Rules for creating new folders

Create a new folder when:

- Multiple related files share a clear responsibility.
- A component is large enough to justify separation.
- It improves maintainability or navigation.
- It represents a distinct application layer or infrastructure component.

Do not create a new folder when:

- It only holds one small file without a meaningful reason.
- An existing folder already has the same responsibility.
- The separation creates unnecessary complexity.
- The folder name does not clearly communicate its purpose.

**Example:**

A monitoring service consisting of a single file can initially live at:

`backend/app/services/monitoring.py`

If monitoring grows into multiple modules, it can become:

```text
backend/app/services/monitoring/
├── __init__.py
├── thresholds.py
├── incident_detector.py
└── notification_service.py
```

---

## 7. File placement decision rules

Before creating a file, answer these questions in order:

1. **Is this application functionality?**  
   Place it under `backend/` or `frontend/`.

2. **Does it configure the operating environment or cloud resources?**  
   Place it under `infrastructure/`.

3. **Is it an executable helper for setup, deployment, monitoring, backup or maintenance?**  
   Place it under `scripts/`, unless it is specifically a server bootstrap script owned by `infrastructure/bootstrap/`.

4. **Does it test application or infrastructure behavior?**  
   Place it in the appropriate component's `tests/` directory or in the root `tests/` for cross-component tests.

5. **Does it explain how something works?**  
   Place it under `docs/`.

6. **Is it specific to GitHub automation?**  
   Place it under `.github/`.

7. **Does it configure or describe the entire repository?**  
   Consider placing it in the project root.

If a file could reasonably fit in multiple locations, choose one authoritative location based on its primary responsibility. Avoid unnecessary duplication.

---

## 8. General prohibited practices

- Do not create folders named `misc/`, `random/` or `temp/` as permanent storage for unrelated project files.
- Do not mix backend and frontend source code.
- Do not place deployable Linux configuration files inside documentation folders.
- Do not put database migration files inside API route folders.
- Do not place runtime logs or database backup files in source directories.
- Do not commit `.venv/`, `__pycache__/`, `node_modules/` or local build artifacts.
- Do not duplicate shared logic across multiple directories without justification.
- Do not reorganize established folders without updating affected imports, scripts, workflows and documentation.

## 9. Final principle

**Organize files by responsibility, not simply by file extension.**

A Python file can belong in the backend, tests, or scripts directory depending on what it does.

A YAML file can belong in `.github/`, `infrastructure/`, or the project root depending on what it configures.

A Bash script can belong in `scripts/` or `infrastructure/bootstrap/` depending on whether it performs an operational task or initializes the infrastructure.

The correct location is determined by the file's purpose, ownership and relationship to the rest of the project.

Keep the structure simple initially and expand it only as the project grows.
