# Run ServerWatch with Docker Compose

The Compose deployment is the VG1 path. Keep the native Ubuntu deployment
available for demonstrating systemd. Start Compose on loopback port 8080, verify
it with its own database, then point public Nginx at it when ready. The native
application and its PostgreSQL data can stay in place during the rehearsal.

| Component | Role |
| --- | --- |
| `db` | PostgreSQL 17 with no published port and a named volume for its data. |
| `migrate` | One-off job that assigns PostgreSQL roles, runs Alembic as the schema owner, and grants FastAPI its runtime permissions. |
| `api` | Non-root FastAPI process on the private Compose network. |
| `web` | React built with Node and served by Nginx, including same-origin routes for the API and Swagger. |
| Host collector | Runs on the system being measured and posts to the loopback web port. |

Docker Engine with the Compose plugin and Bash are needed on the Linux host.
Python 3.11+ is needed to prepare private configuration and run the optional
host collector. Git is needed to clone and update the repository. The images
provide PostgreSQL, Nginx, and the Node/npm frontend build. A host Nginx and
Certbot are needed to expose the stack under your own HTTPS domain. The full
EC2 `setup.sh` prepares Docker Engine and Compose. Verify `docker compose version`
and `docker info` as the trusted Compose operator before deployment. If the
operator needs access to the default Docker socket, grant the chosen account
membership in the `docker` group and start a new SSH session. Membership grants
root-equivalent access on the host.

## Start the stack (Bash, Docker Compose)

Run as the trusted Compose operator, with the checkout at `~/serverwatch`.
Create the host configuration once. If upgrading an existing stack, use its
current web port and **absolute path to its existing secret directory**.

```bash
install -d -m 700 "$HOME/.config/serverwatch-delivery"
umask 077
nano "$HOME/.config/serverwatch-delivery/compose.env"
```

Example file contents for an operator named `swoperator`:

```dotenv
SERVERWATCH_WEB_PORT=8080
SERVERWATCH_COMPOSE_SECRETS=/home/swoperator/.config/serverwatch-compose/secrets
```

Use an available port, such as 8197, if 8080 is taken. Both manual and CI
deployments use this file and bind the port to loopback. Use the selected port
in the health checks, collector, and host Nginx upstream below.

```bash
bash scripts/deployment/compose_host.sh prepare
bash scripts/deployment/compose_host.sh config --quiet
bash scripts/deployment/compose_host.sh up -d --build --wait
bash scripts/deployment/compose_host.sh ps -a
```

`prepare` reads the secret directory from Compose configuration and creates any
missing private files using the operator's numeric ownership. It preserves
existing files, including the PostgreSQL and API credentials.

### Upgrade an existing Compose volume

Keep the same Compose project and volume. Back up the database and verify the
backup before the upgrade. Run `compose_host.sh prepare` as above before the
first rollout to add the migration password. Then bring up the stack using the
same configuration. Provisioning transfers ownership of `public`, the two
application tables, and Alembic's version table to `serverwatch_migrator`.
FastAPI's existing login keeps its password and can read/insert metrics and
read/create/update/delete incidents. PostgreSQL keeps the database itself under
the administrator role. FastAPI receives only its runtime password.

Rerun the same commands after fixing a startup problem. Inspect
`bash scripts/deployment/compose_host.sh logs migrate api web` if startup fails.
Keep the volume and credentials in place.

## Verify the deployment (HTTP, Bash)

```bash
curl -f http://127.0.0.1:8080/
curl -f http://127.0.0.1:8080/api/v1/health?server_id=1
curl -f http://127.0.0.1:8080/openapi.json
```

Open `http://127.0.0.1:8080/docs` from a browser on the same host. For a
browser on your computer while using an EC2 instance, verify through your
existing access route or configure HTTPS below. Use demo mode until you have an
encrypted route to authenticated endpoints.

## Collect host metrics (Python, FastAPI)

In a second terminal on the Docker host, use the native deployment's Python
virtual environment, or create one from `backend/requirements.txt` first.

```bash
.venv/bin/python scripts/monitoring/collect_local.py \
  --env-file "$HOME/.config/serverwatch-compose/secrets/collector.env" \
  --api-port 8080
```

The collector reads the Docker host's CPU, memory, and disk usage, and sends
samples every five seconds. The host identity snapshot is created by
`prepare_compose.sh` from the same machine. Compose's metrics and incident
records are separate from the native database.

## Demonstrate persistence (Docker Compose, PostgreSQL)

After recording a metric and stopping the foreground collector, run:

```bash
bash scripts/deployment/compose_host.sh down
bash scripts/deployment/compose_host.sh up -d --wait
```

Reconnect to the dashboard and confirm the previous sample remains. Keep the
named volume when stopping or recreating the stack. Removing the volume removes
its database. Transfer native data only via a deliberately planned backup and
restore, and preserve the native database until a restore has been checked.

## Put the stack behind public HTTPS (EC2, Nginx, Certbot)

Point your domain at the Elastic IP and use host Nginx and Certbot to serve
HTTPS. In the EC2 Nginx site for that domain, proxy requests for the dashboard,
API, and Swagger to `http://127.0.0.1:8080`. Leave the Compose web port bound to
loopback and retain a separate native site or switch the site upstream when
demonstrating the native deployment. Verify the domain from a browser and test
a live incident edit over HTTPS. Certificate provisioning and a live EC2
rehearsal are still required for VG2.

The implementation uses [Compose startup conditions](https://docs.docker.com/compose/how-tos/startup-order/),
[file-backed Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/),
and a [PostgreSQL image volume](https://hub.docker.com/_/postgres?tab=description).
