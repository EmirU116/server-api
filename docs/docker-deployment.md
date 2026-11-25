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
host collector. Install `python3-venv` if using the collector on a Compose-only
host. Git is needed to clone and update the repository. The images
provide PostgreSQL, Nginx, and the Node/npm frontend build. A host Nginx and
Certbot are needed to expose the stack under your own HTTPS domain. The full
EC2 `setup.sh` prepares Docker Engine and Compose. Verify `docker compose version`
and `docker info` as the trusted Compose operator before deployment. If the
operator needs access to the default Docker socket, grant the chosen account
membership in the `docker` group and start a new SSH session. Membership grants
root-equivalent access on the host.

## Start the stack (Bash, Docker Compose)

Run as the trusted Compose operator, with the checkout at `~/serverwatch`.
For a fresh host or a normal manual restart, run:

```bash
bash scripts/deployment/compose_host.sh start
```

This creates a private host configuration when needed, prepares the Compose
secrets, builds the images, and shows service status after startup. The default
web address is `127.0.0.1:8080`. It reuses existing settings and credentials.
If port 8080 is occupied, edit `SERVERWATCH_WEB_PORT` and run `start` again.

### Customize host settings

For a different port or secret directory, edit the private host configuration.
When upgrading a stack, use its current web port and **absolute path to its
existing secret directory**.

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

To see the Compose dashboard on your computer, add
`-L 8080:127.0.0.1:8080` to your working SSH command, run it locally, and leave
that session open. Open `http://localhost:8080/` and choose **Connect your API**.
Use the `reader_token` from the configured Compose secret directory on EC2.
Retrieve it privately. Adjust the tunnel destination port if you customized
the Compose web port. The public Nginx site continues serving its configured
upstream until you change it.

## Collect host metrics (Python, FastAPI)

In a second EC2 terminal, from the checkout, run:

```bash
bash scripts/deployment/compose_host.sh collect
```

The command finds the published Compose port and collector configuration and
uses the project virtual environment that `setup.sh` created. The collector runs in that terminal until
you press Ctrl+C. It reads the Docker host's CPU, memory, and disk usage, and sends
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

The [HTTPS setup](ec2-manual-setup.md#custom-domain-and-https-with-certbot-vg2)
points the domain at the native deployment. To serve the Compose stack on the
domain instead, edit the `listen 443 ssl` block in
`/etc/nginx/sites-enabled/serverwatch-domain.conf`: keep the `server_name` and
`ssl_*` lines, and replace `root`, `index` and the three `location` blocks with
`location / { proxy_pass http://127.0.0.1:8080; }`. The Compose `web` container
already serves React and proxies the API. Run `sudo nginx -t`, then
`sudo systemctl reload nginx`. Leave the Compose web port bound to loopback.

The implementation uses [Compose startup conditions](https://docs.docker.com/compose/how-tos/startup-order/),
[file-backed Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/),
and a [PostgreSQL image volume](https://hub.docker.com/_/postgres?tab=description).
