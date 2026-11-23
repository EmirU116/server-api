# Run ServerWatch with Docker Compose

The Compose deployment is the VG1 path. Keep the native Ubuntu deployment
available for demonstrating systemd. Start Compose on loopback port 8080, verify
it with its own database, then point public Nginx at it when ready. The native
application and its PostgreSQL data can stay in place during the rehearsal.

| Component | Role |
| --- | --- |
| `db` | PostgreSQL 17 with no published port and a named volume for its data. |
| `migrate` | One-off job that provisions the restricted application role and runs Alembic before FastAPI starts. |
| `api` | Non-root FastAPI process on the private Compose network. |
| `web` | React built with Node and served by Nginx, including same-origin routes for the API and Swagger. |
| Host collector | Runs on the system being measured and posts to the loopback web port. |

Docker Engine with the Compose plugin and Bash are needed on the Linux host.
Python 3.11+ is needed to prepare private configuration and run the optional
host collector. Git is needed to clone and update the repository. The images
provide PostgreSQL, Nginx, and the Node/npm frontend build. A host Nginx and
Certbot are needed to expose the stack under your own HTTPS domain.

## Start the stack (Bash, Docker Compose)

Run as the user who will operate Compose.

```bash
bash scripts/setup/prepare_compose.sh
export SERVERWATCH_RUNTIME_UID="$(id -u)"
export SERVERWATCH_RUNTIME_GID="$(id -g)"
docker compose config --quiet
docker compose up -d --build --wait
docker compose ps -a
```

The setup script creates private files under the ignored `secrets/` directory,
including separate database passwords and separate reader, collector, and
incident admin tokens. Rerunning it preserves existing files. Compose bind
mounts these files using their numeric host ownership. Use the same account to
prepare the files and launch Compose. To keep private files outside the checkout,
set `SERVERWATCH_COMPOSE_SECRETS` to an absolute private directory before setup
and keep that variable set for subsequent Compose commands.

If starting the stack fails, check `docker compose logs migrate api web` and
the status of `db` with `docker compose ps -a`. If startup cannot bind 8080,
choose a free host port with `SERVERWATCH_WEB_PORT`.

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
  --env-file "${SERVERWATCH_COMPOSE_SECRETS:-$PWD/secrets}/collector.env" \
  --api-port "${SERVERWATCH_WEB_PORT:-8080}"
```

The collector reads the Docker host's CPU, memory, and disk usage, and sends
samples every five seconds. The host identity snapshot is created by
`prepare_compose.sh` from the same machine. Compose's metrics and incident
records are separate from the native database.

## Demonstrate persistence (Docker Compose, PostgreSQL)

After recording a metric and stopping the foreground collector, run:

```bash
docker compose down
docker compose up -d --wait
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
