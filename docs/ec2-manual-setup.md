# EC2 manual setup and deployment rehearsal (AWS, Ubuntu, Bash, Git)

This guide walks through creating a fresh Ubuntu EC2 instance, cloning the
project, checking that the instance can pull a later GitHub change, and running
the current native ServerWatch monitoring setup. It is a rehearsal guide, not an
AWS provisioning script. Follow the course requirement to create the instance
from scratch during the recorded assessment.

## What is ready, and what is still pending

The current Ubuntu installer configures local PostgreSQL, migrations, the
FastAPI service, and the host collector. The read-only verifier checks that the
services work and fresh measurements are stored. The setup runs services as the
normal Linux user who runs the installer.

Use the [account provisioning guide](ubuntu-accounts.md) if you are showing
separate junior and senior workspaces. The deployment still uses one checkout
owned by the installing SSH user. Track assignment evidence in the
[project plan](project-plan.md).

### Packages for each deployment path

| Path | Packages |
| --- | --- |
| Before cloning | Ubuntu 24.04+, `git`, `openssh-client` on the student computers and SSH server on EC2, Bash, and sudo. |
| Native setup | `git`, `python3`, `python3-venv`, `python3-pip`, `postgresql`, `postgresql-client`, `iproute2`, `nginx`, `curl`, `cron`, `ca-certificates`, and `xz-utils`. FastAPI and the other Python dependencies are installed into the project virtual environment. |
| Native frontend build | Full setup reuses Node.js 22.12+ with npm when available. Otherwise it downloads Node.js 22 and npm from nodejs.org, verifies the archive checksum, and uses a per-user installation for the React build. |
| Optional account provisioning | `acl` for managed workspace permissions. |
| Scheduled backups (G5) | The full native installer installs Cron, PostgreSQL client tools, and the [native backup schedule](#verify-cron-backups-and-restore-g5). |
| VG deployment | Full setup installs Ubuntu's `docker.io`, `docker-compose-v2`, and `docker-buildx` on a fresh host, then enables Docker. Follow the [Compose guide](docker-deployment.md) to start the stack. Certbot and its Nginx plugin are separate prerequisites for custom-domain HTTPS. |

The full installer runs after checkout. If Git is missing, install it before
the first clone:

```bash
sudo apt-get update
sudo apt-get install -y git
```

## 1. Prepare the repository and local SSH keys

1. Push the code you intend to rehearse to GitHub. Record the commit with
   `git rev-parse main` and make sure the local working tree is clean.
2. Check whether the repository is public or private. A public repository can
   be cloned by EC2 without a GitHub account. For a private repository, prepare
   a repository-scoped read-only deploy key or another approved read-only
   authentication method; never place a personal token in a clone URL.
3. Each student creates their own SSH key pair on their own computer. Keep each
   private key on its owner's computer. The instance's initial EC2 key pair is
   for initial access; do not send private keys to the other student.
4. Note each student's current public IP address. Security group SSH rules must
   allow both students to connect. If they share a changing network, update the
   SSH source rule when the public IP changes.

## 2. Launch a fresh Ubuntu EC2 instance (AWS Console)

1. Open the EC2 console and choose the intended AWS Region. Confirm the account
   and Region before creating resources.
2. Choose **Launch instance**. Give it a recognizable name such as
   `serverwatch-rehearsal`.
3. Select a current Ubuntu Server LTS AMI supported by the project setup guide
   (Ubuntu 24.04 or newer). Select an instance type marked eligible for the
   course's free-tier settings in the console. Check current AWS pricing and
   course account limits before launch; eligibility and charges depend on the
   account and Region.
4. Create or select an EC2 key pair for the initial `ubuntu` login and download
   its private key to a safe local location. You cannot download that private
   key again from EC2.
5. Under network settings, use a public subnet with a public IPv4 address so
   SSH and package installation can work. Create a security group with only
   these inbound rules initially:

   | Type | Port | Source | Reason |
   |---|---:|---|---|
   | SSH | 22 | Bob's current public IP `/32` and Alice's current public IP `/32` | Remote administration |

   Do **not** open PostgreSQL port 5432 or FastAPI port 8000 to the internet.
   Add the HTTP rule after verifying the Nginx setup below.
6. Review the storage size and instance settings against current course/free-tier
   limits. Launch the instance and wait for both EC2 status checks to pass.
7. Allocate an Elastic IP and associate it with the instance if the assignment
   requires one. Check current AWS billing before allocating; idle or otherwise
   billable public IPv4 resources may incur charges. Record the instance ID,
   Region, and public/Elastic IP for the rehearsal.

AWS references: [launch an EC2 instance](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-launch-instance-wizard.html),
[connect to a Linux instance](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-to-linux-instance.html),
and [associate an Elastic IP](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/working-with-eips.html).

## 3. Connect as the initial Ubuntu user

From each student's terminal, use that student's private key. For example:

```bash
ssh -i /path/to/initial-ec2-key.pem ubuntu@ELASTIC_IP
```

On Linux/macOS, restrict the private key permissions if SSH asks:

```bash
chmod 400 /path/to/initial-ec2-key.pem
```

For Windows, use the OpenSSH client in PowerShell or Git Bash and the correct
path to the `.pem` file. Confirm the host fingerprint when connecting. Both
students must verify they can connect before proceeding. If the second student
does not have the initial key, add that student's **public** key to the
appropriate Linux account; never copy the first student's private key.

The finished project should use distinct human accounts if you choose to
demonstrate user-level access. That account/group setup is future work, so this
current installer rehearsal uses one normal setup account. Do not assume that
adding two public keys to the same `ubuntu` account demonstrates Linux user and
group permissions.

## 4. Clone the repository on EC2

On the instance, as the normal `ubuntu` user (not root):

```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/EmirU116/server-api.git "$HOME/serverwatch"
cd "$HOME/serverwatch"
git status --short --branch
git log -1 --oneline
```

This is the project checkout that will run on the instance. Clone it once for
the deployment; Bob and Alice do not need separate copies just to use the
server. If the repository is private, use the read-only authentication method
prepared in step 1. Never put a token or private key in a command, URL, or
tracked file.

For the SCP demonstration, run this on your computer from the checkout:

```bash
scp -i /path/to/initial-ec2-key.pem setup.sh ubuntu@ELASTIC_IP:~/setup.sh
```

On EC2, run the transferred entry point against the cloned project:

```bash
SERVERWATCH_PROJECT_DIR="$HOME/serverwatch" bash "$HOME/setup.sh" ELASTIC_IP
```

For normal setup and updates, run `bash setup.sh ELASTIC_IP` inside the
checkout. You can optionally pass the EC2 public DNS hostname as a second
argument. Use your normal SSH user. The script uses sudo for package and
service changes and keeps existing credentials and PostgreSQL data.
It deploys native FastAPI, PostgreSQL, the systemd collector, React through
Nginx, and Cron backups. It installs Docker tooling and adds the Bash aliases
`sw-status`, `sw-logs`, `sw-timers`, and `sw-help` for new SSH sessions.
Run `sw-help` to see the available shortcuts.

For a combined rehearsal, export only the options that apply to your demo,
then run setup and verification in the same SSH session:

```bash
export SERVERWATCH_SENIOR_USER=emir
export SERVERWATCH_JUNIOR_USER=alice
export SERVERWATCH_DISCORD_WEBHOOK_FILE="$HOME/.config/serverwatch-alerts/discord-webhook"
export SERVERWATCH_START_COMPOSE=1
bash setup.sh ELASTIC_IP
bash verify.sh ELASTIC_IP
```

Create the [private webhook file](discord-alerts.md) first. Discord defaults
to 90%; export `SERVERWATCH_DISCORD_THRESHOLD` to change it. The developer
roles grant permissions to `/srv/serverwatch/dev` and `/srv/serverwatch/prod`.
Install each student's SSH public key separately. Compose startup requires
the checkout at `~/serverwatch` and an operator with [Docker access](docker-deployment.md).
Keep the account options for the same names on subsequent runs.

Verification checks the native API, collector, React and Nginx, Cron setup,
Docker tooling, aliases, and selected integrations. Demonstrate public
routing from your computer, Discord delivery, the scheduled backup and restore,
and Compose persistence using the corresponding walkthroughs.

If a host still has the retired API-only test service, inspect it with
`sudo systemctl status serverwatch-ec2-test.service`. If it is the old
ServerWatch smoke test and you are replacing it, stop and disable it with
`sudo systemctl disable --now serverwatch-ec2-test.service`.

## 5. Verify the current native monitoring deployment

From the EC2 checkout, still as the installing user:

```bash
cd "$HOME/serverwatch"
bash verify.sh ELASTIC_IP
```

Expected: all checks pass, including active PostgreSQL/API/collector services,
loopback-only listeners, server identity matching the Ubuntu host, a healthy
database check, and a newly stored metrics sample. The verifier waits for a
fresh sample. It is read-only and does not create incident records.

Inspect service state and recent logs if needed:

```bash
sudo systemctl status serverwatch-api serverwatch-collector postgresql --no-pager
sudo journalctl -u serverwatch-api -u serverwatch-collector -n 50 --no-pager
```

Reboot once during rehearsal, reconnect by SSH, and rerun the verifier. The API
and collector should return because their systemd units are enabled. Keep the
database and services private: ports 5432 and 8000 should listen only on
loopback, and their security group inbound rules should be absent.

## 6. Test that EC2 can pull a new public-repository change

Do this after the first deployment is verified:

1. On your development computer, create a small harmless documentation change on
   a feature branch. Run the relevant local checks, commit it, push the branch,
   and open a pull request to `main`.
2. Wait for required CI checks. Review and merge the PR. This ensures EC2 pulls
   a reviewed commit from `main`, not unfinished feature work.
3. On EC2, check that the working tree is clean and record the deployed commit:

   ```bash
   cd "$HOME/serverwatch"
   git status --short --branch
   git rev-parse HEAD
   ```

4. Pull the merged change:

   ```bash
   git pull --ff-only origin main
   git log -1 --oneline
   git status --short --branch
   ```

   Confirm the latest commit matches the merged GitHub commit and the working
   tree is clean. This demonstrates GitHub-to-EC2 update access. It does not
   itself restart or deploy application code.
5. For an application-code change, follow a reviewed deployment procedure:
   check release notes and migrations, install changed dependencies, apply the
   explicit database migration if required, restart the API/collector, then run
   the verifier. The current installer is a maintenance operation that can
   restart services; review [its behavior](ubuntu-monitoring.md#setup-bash-ubuntu-packages-postgresql)
   before rerunning it. Do not use the docs-only pull test as evidence that a
   code deployment or rollback works.

If GitHub says the repository is public, no GitHub login is needed on EC2 for
clone/pull. For a private repository, verify that the instance's read-only key
can fetch without granting write access. Do not create a personal GitHub account
for the server.

## 7. Serve the dashboard and API through Nginx (Bash, React, FastAPI)

The setup command in step 4 already builds and publishes React, configures
Nginx, enables Swagger and OpenAPI, and verifies the web routes over loopback.
For an update, use `git pull --ff-only` on a clean checkout, then rerun that same
setup command. It applies pending migrations before publishing the dashboard.

For a failure, rerun `bash verify.sh ELASTIC_IP`. Use `sudo nginx -t` and
`sudo journalctl -u nginx -u serverwatch-api -n 50 --no-pager` for details.
To explain the proxy during the demo, navigate to `/etc/nginx/sites-enabled`
and open `serverwatch.conf` in your editor.

1. In the EC2 security group, add an inbound **HTTP / TCP 80** rule from your
   public IPv4 address with a `/32` suffix. Add your teammate's or assessor's
   source if they need access. Use `0.0.0.0/0` only if open access is intended.
   Keep ports 8000 and 5432 closed. If you enabled a host firewall, allow the
   same HTTP traffic there.
2. On your computer, open these URLs using the public IP. No SSH tunnel is needed.

   | URL | Expected result |
   | --- | --- |
   | `http://EC2_PUBLIC_IP/` | React dashboard loads in demo mode |
   | `http://EC2_PUBLIC_IP/api/v1/health?server_id=1` | JSON reports healthy, with server and database up |
   | `http://EC2_PUBLIC_IP/docs` | Swagger lists the ServerWatch endpoints |
   | `http://EC2_PUBLIC_IP/openapi.json` | JSON contains the API schema and paths |

   HTTP sends bearer tokens in plaintext. Use demo mode, public health and
   unauthenticated Swagger for this HTTP rehearsal. Use **Connect API** with
   the reader token after HTTPS is in place, or through the SSH tunnel for a
   private live test. If EC2 verification passes but these URLs time out,
   check the public IP, security group, and host firewall.

## 8. Record evidence and clean up

Keep a short rehearsal record: instance ID and Region, AMI/instance type,
security-group rules, Elastic IP association, each student's successful SSH
login, repository commit before/after pull, verifier summary, and reboot result.
Never include private keys, API tokens, database passwords, or secret file
contents in screenshots or notes.

Before stopping the rehearsal, record the evidence you need, then stop or
terminate the EC2 instance as intended and release an unused Elastic IP. Confirm
the instance is no longer running and review the AWS console for leftover
billable resources. The course recording must use a newly created instance, so
rehearse this process separately from the recorded fresh-instance run.

## Verify Cron backups and restore (G5)

Full setup installs a root-owned command at `/usr/local/sbin/serverwatch-backup`
and a schedule at `/etc/cron.d/serverwatch-backup`. Every day at 03:15 in the
host's timezone, Cron saves a custom-format dump of the **native**
`serverwatch_monitor` database and the past 24 hours of native service logs.
Completed snapshots are kept in private directories under
`/var/backups/serverwatch`. Keep an eye on disk space and remove old snapshots
according to your team's retention needs. These snapshots live on the EC2 disk.

For the demo, inspect the schedule with `sudo cat /etc/cron.d/serverwatch-backup`.
Use `sudoedit /etc/cron.d/serverwatch-backup` to set the schedule to the next minute
and wait for Cron to run it. Restore the normal schedule after it runs. Verify
the scheduled run and find the completed snapshot:

```bash
sudo journalctl -t serverwatch-backup -n 10 --no-pager
sudo ls -lt /var/backups/serverwatch
```

On EC2, substitute the snapshot directory name in the command below. This creates
a separate database and shows counts from the restored tables. Capture a metric
timestamp from the native API before the backup and verify it exists in the restored
database for the demo. Run the commands in Bash as your usual SSH user.

```bash
(
    set -euo pipefail
    unset PGHOST PGHOSTADDR PGPORT PGSERVICE PGSERVICEFILE
    snapshot=/var/backups/serverwatch/REPLACE_WITH_SNAPSHOT_DIRECTORY
    restore_db="serverwatch_restore_$(date +%s)"
    sudo -u postgres createdb --host=/var/run/postgresql --port=5432 "$restore_db"
    sudo cat "$snapshot/database.dump" |
        sudo -u postgres pg_restore --host=/var/run/postgresql --port=5432 \
            --exit-on-error --no-owner --no-privileges --dbname="$restore_db"
    sudo -u postgres psql -X --host=/var/run/postgresql --port=5432 \
        --set=ON_ERROR_STOP=1 --dbname="$restore_db" \
        -c 'SELECT count(*) AS metrics, max(collected_at) AS latest FROM metrics' \
        -c 'SELECT count(*) AS incidents FROM incidents'
    printf 'Restored database: %s\n' "$restore_db"
)
```

`sudo /usr/local/sbin/serverwatch-backup` runs the same backup immediately for
troubleshooting. Use the Cron log as evidence of the scheduled run.

## Current limits and next steps

Record the public-IP browser checks as evidence for the native Nginx deployment.
Configure and demonstrate the [Discord timer](discord-alerts.md) and, if using
separate role accounts, verify their [workspace permissions](ubuntu-accounts.md).
Verify the scheduled backup and restore on EC2. For VG, run the
[Compose stack](docker-deployment.md) on EC2 and verify database persistence.
Point a custom domain at EC2, obtain a Certbot certificate, then verify HTTPS,
HTTP redirects, and renewal.
See the [assignment coverage tracker](project-plan.md#assignment-coverage-tracker)
and [GitHub/EC2 workflow](github-actions-plan.md#opt-in-deployment-workflow-github-actions-compose-ec2).
