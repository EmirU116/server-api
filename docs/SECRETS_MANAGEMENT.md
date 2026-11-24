# ServerWatch — Secrets Management Guide

**Project stack:** FastAPI · PostgreSQL · Docker Compose · Ubuntu EC2 · Nginx · GitHub Actions

## 1. Purpose

Keep credentials **out of source code, Git history, Docker images, and public logs**. Each process receives only the secrets it needs. This guide describes where ServerWatch's real credentials live and the rules for handling them.

> **Approach for the assignment:** an ignored `.env` file for local development, private mode-600 files generated on EC2 for the native and Compose deployments, and a root-owned file for the Discord webhook. AWS Secrets Manager is a possible later improvement, not required for the VG demo.

## 2. Where each secret lives

| Secret | Local development | Native EC2 (`setup.sh`) | Compose on EC2 |
|---|---|---|---|
| Database password | `.env` (`SERVERWATCH_DATABASE_PASSWORD` or `_FILE`) | `~/.config/serverwatch-monitoring/db_password` | `db_password`, plus `db_admin_password` and `db_migration_password` for setup and migrations |
| Reader, collector, admin tokens | `.env` (`SERVERWATCH_{READER,COLLECTOR,ADMIN}_TOKEN` or `_FILE`) | `~/.config/serverwatch-monitoring/{reader,collector,admin}_token` | `reader_token`, `collector_token`, `admin_token` |
| Discord webhook URL | Not used | `/etc/serverwatch-discord/webhook` (root, mode 600) | Not used |
| Student SSH private keys | Each student's own computer | **Never** on EC2; only public keys in `authorized_keys` | Same |
| HTTPS certificate private key | Not applicable | Managed by Certbot in `/etc/letsencrypt/` | Same |

The Compose files live in the secret directory set in `~/.config/serverwatch-delivery/compose.env` (default `~/.config/serverwatch-compose/secrets`). Real values never go in `.env.example`, the checkout, Docker images, or Git. `.gitignore` excludes `.env`, `secrets/`, key files and `.aws/`. Adding a file to `.gitignore` does **not** remove a secret that was already committed; rotate it instead.

## 3. Local development

Copy `.env.example` to `.env` and replace the placeholders privately. The application reads only `SERVERWATCH_*` settings (see the README's settings table). Load the file explicitly with Uvicorn's `--env-file .env`; tests never read it. For each secret, a `*_FILE` setting pointing to a protected file takes precedence over the plain variable, which avoids dotenv quoting problems.

Startup fails with a sanitized message, without echoing values, when a configured secret is blank, contains whitespace (tokens), or when a configured file cannot be read. The three role tokens must all differ.

## 4. Native Ubuntu deployment

`setup.sh` (through `setup_ubuntu_monitoring.sh` and `scripts/setup/configure_ubuntu.py`) creates `~/.config/serverwatch-monitoring/` with mode 700 and generates each secret once as a mode-600 file. Reruns keep existing values and refuse files with the wrong owner, mode, or a symlink. The project's `.env` is never imported.

- `api.env` points the API service to the secret files.
- `collector.env` gives the collector **only** its token file.
- Both services run as the setup user, so this is not isolation from other processes owned by that same user.
- Database provisioning sends a SCRAM verifier to `psql` through stdin and suppresses raw SQL errors. Never run setup with shell tracing (`bash -x`). Passwords and tokens never appear in command arguments.

The [Discord alert setup](discord-alerts.md) copies the webhook to `/etc/serverwatch-discord/webhook`. systemd's `LoadCredential` exposes it only to the alert service during a check; the API, collector and frontend never receive it.

## 5. Compose deployment

`compose_host.sh start` (or `prepare`) runs `scripts/setup/prepare_compose.sh`, which creates the secret directory (mode 700) and generates each file once (mode 600). Compose mounts the files under `/run/secrets/`; the API reads them through its `*_FILE` settings. Mounted secrets are still plain files on the EC2 disk: protect the directory, backups and logs, and restrict who can run Docker, since Docker administrators can read container secrets.

- The one-shot `migrate` service receives all three database passwords so it can create the roles and grant runtime access. The API receives only its runtime database password, the role tokens and the host identity file.
- PostgreSQL stays on an internal Compose network with no published port.
- `collector.env` in the secret directory lets the host collector (`compose_host.sh collect`) use the Compose collector token without touching the native configuration.

Never solve a permission problem with `chmod 777`.

## 6. Role tokens and the frontend

- Readers call GET endpoints, the collector posts metrics, and the admin creates, edits and deletes incidents. Roles do not inherit each other's permissions.
- Send `Authorization: Bearer <token>`. Never log this header or a webhook URL.
- The dashboard keeps the reader token, and the optional admin token, in React memory only, never in build variables or browser storage, and accepts them only over HTTPS or localhost.
- Never give the collector token or database passwords to the frontend.

## 7. GitHub Actions

The CI workflow runs tests only and uses no repository secrets. There is no automatic deployment. If one is added later (VG4 bonus), store credentials as environment-scoped GitHub Actions secrets restricted to `main`, prefer GitHub OIDC with an IAM role over long-lived AWS keys, and keep the deploy account's permissions narrow. A deploy must not print credentials or overwrite production secret files.

## 8. AWS Secrets Manager — optional enhancement

For a more advanced deployment, put secret values into **AWS Secrets Manager** (or encrypted Systems Manager Parameter Store). Give EC2 an IAM role granting access only to the specific secrets it needs, retrieve them at runtime or deployment time, and rotate them periodically. This reduces reliance on manually managed files, but adds IAM work, cost considerations, and integration complexity. It is **not necessary to satisfy the VG criteria**.

## 9. When credentials leak or need rotation

1. **Revoke or rotate** the affected password, key or webhook immediately.
2. Replace it in the correct location from section 2; update every dependent service.
3. Restart affected processes so they load the new value (`sudo systemctl restart serverwatch-api serverwatch-collector`, or recreate the Compose services).
4. Inspect logs, Git history and CI output for accidental exposure; clean history if necessary, but remember that history rewriting alone does not revoke leaked secrets.
5. Record what happened without copying the secret into an issue or report.

Setup never overwrites an existing secret file, so to rotate one, replace the file's contents yourself (keeping mode 600) before restarting. Rotating a database password also requires changing it in PostgreSQL.

## 10. Developer and AI-agent rules

**Allowed:** add placeholders to `.env.example`; write code that loads secrets securely; document expected variable names; propose least-privilege policies; add tests with fake credentials.

**Not allowed without explicit approval:** read, print, copy, expose, upload, commit, rotate or delete real secrets; change production credentials; modify EC2 IAM/SSH settings; alter GitHub secrets; or deploy with elevated access.

### Final checklist

- [ ] No real credentials in Git, source files, documentation or images.
- [ ] `.gitignore` excludes all real secret files.
- [ ] FastAPI fails safely if a required credential is missing.
- [ ] PostgreSQL listens only on loopback (native) or the internal Compose network.
- [ ] Local testing uses dummy/test secrets.
- [ ] EC2 secret directories are mode 700 and files mode 600, owned by the right account.
- [ ] Secrets are not printed in logs or error messages.
- [ ] Rotation and recovery steps are documented and rehearsed.

**Principle:** Source code describes *how* the system works; secret storage supplies *which credentials* it may use.
