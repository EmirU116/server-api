# Start monitoring an Ubuntu host (Bash, Python, PostgreSQL, systemd)

These scripts turn an existing ServerWatch checkout into a native host monitoring
setup. The Python collector measures the Ubuntu machine where it runs, sends a
sample to local FastAPI, sleeps five seconds, and repeats. PostgreSQL stores the
samples. systemd keeps the API and collector running after logout and reboot.

## Requirements (Ubuntu, SSH, Bash)

- Native Ubuntu 24.04 or newer with systemd, Python 3.11+, and internet access for
  Ubuntu/Python packages. WSL and containers are intentionally rejected.
- A normal SSH user with sudo access and a checkout owned by that user.
- Project/home paths without spaces or special characters. Keep the checkout
  at the same path after installing the services.
- Local PostgreSQL's default port 5432 and API port 8000. A pre-existing API on
  port 8000 must be stopped explicitly before setup.

The scripts use a local PostgreSQL database, not RDS. They do not create AWS
resources or alter security groups/firewalls. Running them on an existing paid
server uses that server's resources and disk space.

## Setup (Bash, Ubuntu packages, PostgreSQL)

For the full EC2 deployment, use the root `setup.sh`. It also prepares
Node.js/npm, publishes React and Swagger through Nginx, and installs Docker
tooling and Cron. See the [EC2 guide](ec2-manual-setup.md#packages-for-each-deployment-path).

Clone or transfer the current code first. On the Ubuntu server, from the project
root, run as your normal SSH user:

```bash
bash infrastructure/bootstrap/setup_ubuntu_monitoring.sh
```

Do not put `sudo` before the whole command. The script requests sudo for package,
PostgreSQL, and systemd administration. From another directory, pass the clone's
absolute path:

```bash
bash /home/ubuntu/serverwatch/infrastructure/bootstrap/setup_ubuntu_monitoring.sh /home/ubuntu/serverwatch
```

Setup performs these steps:

1. Checks Ubuntu/systemd, checkout ownership assumptions, conflicting managed
   services, and whether port 8000 is free (or our API is already running).
2. Installs Python/venv/pip, PostgreSQL/client, and iproute2 from Ubuntu.
   Creates `.venv` and installs pinned backend runtime requirements, including
   FastAPI and Uvicorn.
3. Creates private managed configuration under
   `~/.config/serverwatch-monitoring/` (directory 700, files 600).
4. Generates separate reader, collector, admin, and database secrets only when
   absent. It never imports a Windows/project `.env` or prints the secret values.
5. Starts/enables local PostgreSQL. Creates a dedicated `serverwatch_monitor`
   login and database if absent. The role has no superuser, database creation,
   role creation, replication, or RLS-bypass privileges; it owns its own database.
   A SCRAM verifier goes to psql through stdin; plaintext passwords are never SQL
   arguments. Existing roles/passwords/data are not reset.
6. Applies the current Alembic upgrade explicitly, creating metrics/incidents
   storage. No schema changes happen implicitly during API startup.
7. Installs/enables/restarts `serverwatch-api.service` and
   `serverwatch-collector.service` as the installing SSH user. API binds only to
   `127.0.0.1:8000`, runs in production mode without reload or Swagger, and uses
   the private configuration. Collector runs directly on the host.
8. Runs verification. Setup exits nonzero if a component fails verification.

Existing configuration must match this managed local database/server-ID setup.
Reruns preserve files and data; they reinstall dependencies, apply new migrations,
and restart the managed services. They are maintenance operations, not a rollback
or a zero-downtime deployment. Configuration/credential mismatches fail safely
instead of silently replacing an existing database's password. A partial failure
may leave installed packages, created files/database, or services in place; fix
the reported issue and rerun. No automatic destructive cleanup is performed.

If the older smoke-test service is running, stop it before setup:

```bash
sudo systemctl disable --now serverwatch-ec2-test.service
```

Only do this when switching away from that older test setup. The new scripts do
not stop unrelated applications or services to reclaim ports.

## Verification (Bash, HTTP, PostgreSQL)

Run as the same user who installed the services:

```bash
bash scripts/verification/verify_ubuntu_monitoring.sh
```

For a narrower, read-only check of the managed configuration after setup, run
this from the repository root as the installing user:

```bash
.venv/bin/python scripts/setup/configure_ubuntu.py validate "$HOME/.config/serverwatch-monitoring"
```

Success is silent with exit status 0. A failure prints a short message and exits
nonzero. This checks private file ownership and permissions, expected settings,
and credential consistency. Use the Bash verifier above to also check running
services, database connectivity, and fresh metrics.

The Bash verifier runs on the Ubuntu server and uses a Python helper for
credential handling, HTTP responses, and database checks. It observes measurements
written by the running collector. It prints PASS/FAIL and a summary, and returns
0 when all of the following checks pass.

| Check | Expected result |
| --- | --- |
| Host/runtime | Native Ubuntu with systemd; Python dependencies consistent |
| Services | PostgreSQL, API, and collector enabled and active |
| Configuration | Private directory/files owned by setup user; distinct tokens; local managed database |
| Network listeners | Both 8000 and 5432 listening only on loopback |
| PostgreSQL | Connects; metrics/incidents tables exist; Alembic version matches code |
| Server API | Reader GET 200; hostname/OS match this Ubuntu host |
| Authentication | Missing reader credential returns 401 |
| Health | ID 1 returns 200 with server/database up; negative ID returns 400 |
| Incidents | Reader list returns 200; no incident CRUD test writes |
| Collector/storage | A different sample ID, timestamped during verification, appears in GET metrics |

It allows up to 20 seconds for API startup and then up to 30 seconds to observe a
new sample, plus short request/database timeouts. An active collector that cannot
submit records fails verification. CPU/disk values need not change on every
sample; a new ID/timestamp proves recording continues.

Credential values and response bodies are never printed. Authentication is sent
only to hardcoded localhost using Python HTTPConnection with a three-second
timeout and no redirect following. Verification does not expose credentials in
process arguments. It does not test admin writes or every API failure condition;
those have separate unit/integration tests and the local Windows CRUD smoke test.

## Inspect and stop (systemd, Linux)

```bash
sudo systemctl status serverwatch-api serverwatch-collector --no-pager
sudo journalctl -u serverwatch-api -u serverwatch-collector -n 50 --no-pager
```

Collector messages report success or safe HTTP statuses. Do not enable shell
tracing (`bash -x`) or manually display the setup helper's `database-sql` output:
that internal stream contains a sensitive password verifier.

To stop monitoring and prevent app startup at boot:

```bash
sudo systemctl disable --now serverwatch-collector.service serverwatch-api.service
```

PostgreSQL and saved measurements remain intact. Restart both app services after
changing managed configuration; ordinary reruns should preserve the generated
files. `api.env` contains settings and secret-file paths; `collector.env` contains
only the collector-token path. Both processes currently run as the SSH user;
these file boundaries do not isolate secrets from other processes owned by that
same account. A dedicated service-account deployment is a later hardening step.

## Scope and validation (Testing, Deployment)

This starts backend monitoring. React hosting, public access, Nginx/HTTPS,
AWS networking, Docker, Cron assessment evidence, metric retention, automatic
incident detection, notifications, and backup/restore remain separate tasks.
The five-second collector skips failed samples and retries; it has no durable
queue. Disk usage measures the host root filesystem, not every mounted volume.

For a complete deployment, use the root-level commands in the
[EC2 guide](ec2-manual-setup.md). The commands here diagnose the monitoring stage.
See [API contracts](api.md) and [secret handling](SECRETS_MANAGEMENT.md).

Implementation references: [systemd restart behavior](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
and [PostgreSQL psql execution/error handling](https://www.postgresql.org/docs/current/app-psql.html).

Contributor checks use dummy/private temporary configuration and disposable
PostgreSQL; they never run the installer or modify host services:

```bash
bash -n infrastructure/bootstrap/setup_ubuntu_monitoring.sh
bash -n scripts/verification/verify_ubuntu_monitoring.sh
.venv/bin/python -m pytest tests/test_ubuntu_monitoring.py backend/tests/test_ubuntu_provisioning.py -q
```

A fresh native Ubuntu/EC2 installation and reboot check are still required.
Passing simulated/local tests does not prove apt installation or systemd startup
on an actual server. Keep this limitation explicit in assignment evidence.

## Linux users, groups and permissions

Future task 5.5 defines accounts and verifies effective access on Ubuntu. Today
the installer runs the API and collector as the installing SSH user. Its
`validate` command checks that user's private configuration. The following is a
broader environment layout. Use the [account provisioning guide](ubuntu-accounts.md)
for the implemented junior and senior workspace ACLs and their manual checks.

| Identity | Development workspace | Production releases | Production secrets and administration |
| --- | --- | --- | --- |
| Agent, intern or junior | Read, create, edit and delete project files in the assigned workspace | Read approved code and traverse release directories | No access to secrets, service control or deployment |
| Senior maintainer | Manage all project workspaces | Manage releases, deploy and roll back | Explicitly authorized administration via audited elevation |
| API and collector | No dependency on developers' worktrees | Read their installed code | Separate service accounts, each able to read only its own runtime configuration |

Give each human and agent a distinct Linux account. Define groups for dev writers,
production readers and release maintainers. For example, give a dev group write
and traversal on its assigned subtree under `/srv/serverwatch/dev/`, and give
prod readers read/traversal on approved files under `/srv/serverwatch/prod/`.
Use group inheritance and default ACLs for newly created files. Keep release
parents, service units, executables used by privileged jobs and secrets outside
dev-writable paths. Production services must execute the independently installed
release. Never run code straight from an agent-writable checkout as a privileged
user. [Linux access and default ACLs](https://man7.org/linux/man-pages/man5/acl.5.html)

Directory permissions control access by identity. A process sharing its
developer's account inherits that developer's access. Launch each agent using
its assigned account. Folder ACLs alone still allow access to other ordinarily
readable host paths. If the requirement becomes confinement to a single
workspace, add an OS sandbox or separate VM with explicit mounts. Keep
unrestricted sudo, Docker administration and production credentials away from
development accounts.

The future Bash verifier should report expected versus actual owner, group,
mode and effective ACL for files and parent directories. Use `id`, `stat` and
`getfacl`, then check effective permissions under each representative identity.
Verify a dev writer can create, edit and remove a disposable dev file, a junior
can read approved production code, and agents/juniors cannot write, rename
or delete production files or read private configuration. Check inheritance on
a newly created file and exercise senior and service-account access separately.
Use a disposable fixture with the same permissions for write/delete trials.
The live verifier should remain read-only and must never print secret contents.
