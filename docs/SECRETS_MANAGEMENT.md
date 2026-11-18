# ServerWatch — Secrets Management Guide

**Project stack:** FastAPI · PostgreSQL · Docker Compose · Ubuntu EC2 · Nginx · GitHub Actions

## 1. Purpose

Keep credentials **out of source code, Git history, Docker images, and public logs**. Each service should receive only the secrets it needs. This document covers database passwords, monitoring API keys, Discord webhooks, SSH keys, and eventual user account passwords.

> **Practical approach for the assignment:** use an ignored `.env` file for local development, file-backed Docker Compose secrets on EC2, and GitHub Actions secrets for CI/CD credentials. AWS Secrets Manager is a possible later improvement, not required for the VG demo.

## 2. Where each secret belongs

| Secret | Local development | EC2 deployment | Notes |
|---|---|---|---|
| PostgreSQL application password | Ignored `.env` | Compose-mounted secret file | Never commit it or publish port 5432. |
| Discord webhook URL | Ignored `.env` | Compose-mounted secret file | Treat the URL as a credential. |
| Monitoring API key | Ignored `.env` | Protected file for the host monitoring script; mounted into FastAPI | The API validates each monitoring request. |
| Student SSH private keys | Each student's own computer | **Not** stored on EC2 | Only their **public** keys belong in `authorized_keys`. |
| Automated deployment credential | Not required locally | GitHub Actions secret or safer identity-based deployment | Keep deployment permissions narrow. |
| HTTPS certificate private key | Not applicable | Managed by Certbot in `/etc/letsencrypt/` | Do not commit or copy it into the repository. |
| Website user passwords (if added later) | Test users only | Store **salted password hashes** in PostgreSQL | Use Argon2id or another appropriate password hashing algorithm; never reversible encryption or plaintext. |

## 3. Suggested project files

```text
serverwatch/
├── backend/
│   └── app/
│       └── config.py            # Reads configuration/secrets
├── docs/
│   └── SECRETS_MANAGEMENT.md    # This guide
├── secrets/                     # REAL secret files: ignored by Git
│   ├── db_password.txt
│   ├── discord_webhook.txt
│   └── monitoring_api_key.txt
├── .env                          # LOCAL-only values: ignored by Git
├── .env.example                  # Harmless placeholder names: committed
├── .gitignore
└── compose.yaml
```

Do **not** put any real values into `secrets/` or `.env` in GitHub. Secrets on EC2 must be created or supplied securely when provisioning the **new instance during the exam recording**.

### `.gitignore`

```gitignore
.env
.env.*
!.env.example
secrets/
*.pem
*.key
*.p12
*.pfx
```

If a file was previously committed, adding it to `.gitignore` does **not** remove the secret from Git history; revoke/rotate the compromised credential.

### `.env.example` (safe to commit)

```dotenv
# Copy to .env for local development. Replace placeholders locally.
POSTGRES_USER=serverwatch
POSTGRES_DB=serverwatch
POSTGRES_PASSWORD=REPLACE_LOCALLY
DISCORD_WEBHOOK_URL=REPLACE_LOCALLY
MONITORING_API_KEY=REPLACE_LOCALLY
```

## 4. Local development with FastAPI

Local `.env` files are convenient, but must never be tracked. One simple option is `python-dotenv`:

```python
# backend/app/config.py — local development example
import os
from dotenv import load_dotenv

load_dotenv()  # Reads .env if available; production should inject configuration separately.

POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
MONITORING_API_KEY = os.environ["MONITORING_API_KEY"]
```

Fail fast when a required secret is missing. Never print secret values in exceptions or logs.

## 5. EC2: Docker Compose secrets

**Use file-backed Compose secrets** so the containers receive credentials as files under `/run/secrets/`. The files still exist on the EC2 disk; Compose secrets do *not* automatically encrypt them at rest or replace good Linux permissions.

Minimal example in `compose.yaml`:

```yaml
services:
  api:
    build: ./backend
    secrets:
      - db_password
      - discord_webhook
      - monitoring_api_key
    environment:
      POSTGRES_USER: serverwatch
      POSTGRES_DB: serverwatch
      POSTGRES_HOST: db
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
      DISCORD_WEBHOOK_URL_FILE: /run/secrets/discord_webhook
      MONITORING_API_KEY_FILE: /run/secrets/monitoring_api_key
    depends_on:
      db:
        condition: service_healthy
    ports:
      - "127.0.0.1:8000:8000"  # Nginx proxies from public HTTPS to localhost.
    restart: unless-stopped

  db:
    image: postgres:17
    environment:
      POSTGRES_USER: serverwatch
      POSTGRES_DB: serverwatch
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets:
      - db_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U serverwatch -d serverwatch"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

secrets:
  db_password:
    file: ./secrets/db_password.txt
  discord_webhook:
    file: ./secrets/discord_webhook.txt
  monitoring_api_key:
    file: ./secrets/monitoring_api_key.txt

volumes:
  postgres_data:
```

**Important:** The API service must explicitly read the `*_FILE` paths; setting `POSTGRES_PASSWORD_FILE` is not a built-in FastAPI feature. The official PostgreSQL container supports `POSTGRES_PASSWORD_FILE` during database initialization. The backend's Dockerfile must run Uvicorn on `0.0.0.0:8000` inside the container.

Example secret reader in Python:

```python
from pathlib import Path
import os


def read_secret(name: str) -> str:
    file_path = os.getenv(f"{name}_FILE")
    if file_path:
        return Path(file_path).read_text(encoding="utf-8").strip()
    return os.environ[name]  # Useful for local development; raises if absent.


password = read_secret("POSTGRES_PASSWORD")
webhook = read_secret("DISCORD_WEBHOOK_URL")
monitoring_key = read_secret("MONITORING_API_KEY")
```

The same Python code works with local environment variables or the corresponding `_FILE` paths supplied by Docker Compose.

### Permissions on EC2

- Store the real `secrets/` directory outside tracked Git data, or keep it in the ignored directory above.
- Restrict its directory permissions (commonly `700`) and file permissions (commonly `600`) **to the account that must read them**.
- With file-backed Compose secrets, verify that the chosen container user can actually read mounted files. A non-root container may need appropriately arranged ownership/group permissions; do not solve the problem with `chmod 777`.
- Protect the EC2 host, backups and logs. Restrict who can run Docker commands, since Docker administrators can often access container secrets.
- Keep PostgreSQL off public ports. Only Nginx should receive public HTTP(S) traffic.

## 6. Cron monitoring and API keys

The local test collector `scripts/monitoring/collect_local.py` now submits real
host measurements to `http://127.0.0.1:8000/api/v1/metrics` using a plain loop and
five-second sleep. It loads the collector credential privately and never follows
redirects or prints tokens/response bodies. Production host/Cron scheduling remains
pending. See [local development](local-development.md).
The application now uses `SERVERWATCH_COLLECTOR_TOKEN` or
`SERVERWATCH_COLLECTOR_TOKEN_FILE` for POST, and a different reader token for GET.
Use [local setup](local-postgresql.md) and `.env.example` for the implemented
`SERVERWATCH_*` settings; older generic configuration examples above are illustrative.

- Give the monitoring script a dedicated API key with limited scope.
- Read that key from a protected file accessible to the monitoring user; do not paste it directly into the script or crontab.
- FastAPI must verify the key before accepting submitted metrics.
- Send `Authorization: Bearer <collector token>`; never log this header or a full Discord webhook URL.
- Never give collector credentials or database passwords to the frontend.
- Handle failed API submissions and avoid repeatedly creating duplicate incidents.

### Incident administrator credential

Incident writes require a separate `SERVERWATCH_ADMIN_TOKEN` or
`SERVERWATCH_ADMIN_TOKEN_FILE`; the file takes precedence. Reader, collector, and
admin values must be different. An admin token grants incident POST/PATCH/DELETE,
not reader GET or metric POST permissions. Missing admin configuration disables
incident writes with 503 without disabling other APIs. Create/store the token
privately using [local incident setup](local-postgresql.md#enable-incident-storage-python-postgresql).
Do not put it in frontend build variables, browser storage, logs, or Git.
The current dashboard reader connection must continue using only the reader token.

## 7. GitHub Actions and deployment

Store deployment secrets in **GitHub Actions Secrets**, not in workflow YAML or committed shell scripts. Restrict deployment to the approved branch/environment and use least-privilege credentials. If deploying to AWS APIs, prefer short-lived identity through **GitHub OIDC + IAM role** rather than permanent AWS access keys. For SSH-based deployments, use a narrowly scoped deployment key and protect it as a secret.

A deploy should **not** print credentials, copy production `.env` into Git, or overwrite production secret files during an ordinary release.

## 8. AWS Secrets Manager — optional enhancement

For a more advanced deployment, put secret values into **AWS Secrets Manager** (or encrypted Systems Manager Parameter Store). Give EC2 an IAM role granting access only to the specific secrets it needs, retrieve them at runtime or deployment time, and rotate them periodically. This reduces reliance on manually managed files, but adds IAM work, cost considerations, and integration complexity. It is **not necessary to satisfy the VG criteria**.

## 9. When credentials leak or need rotation

1. **Revoke or rotate** the affected password, key or webhook immediately.
2. Replace it in the correct secret store/location; update every dependent service.
3. Restart/redeploy affected processes so they load the new value.
4. Inspect logs, Git history and CI output for accidental exposure; clean history if necessary, but remember that history rewriting alone does not revoke leaked secrets.
5. Record what happened without copying the secret into an issue or report.

## 10. Developer and AI-agent rules

**Allowed:** add placeholders to `.env.example`; write code that loads secrets securely; document expected variable names; propose least-privilege policies; add tests with fake credentials.

**Not allowed without explicit approval:** read, print, copy, expose, upload, commit, rotate or delete real secrets; change production credentials; modify EC2 IAM/SSH settings; alter GitHub production secrets; or deploy with elevated access.

### Final checklist

- [ ] No real credentials in Git, source files, documentation or images.
- [ ] `.gitignore` excludes all real secret files.
- [ ] FastAPI fails safely if a required credential is missing.
- [ ] PostgreSQL is reachable only on the private Docker network.
- [ ] Local testing uses dummy/test secrets.
- [ ] EC2 secret files have restrictive, working permissions.
- [ ] GitHub Actions uses the smallest required deployment permissions.
- [ ] Secrets are not printed in logs or error messages.
- [ ] Rotation and recovery steps are documented and rehearsed.

**Principle:** Source code describes *how* the system works; secret storage supplies *which credentials* it may use.
