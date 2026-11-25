# Presentation guide (recorded pair demo)

This is the script for the recorded assessment. It follows the order of the
[assignment brief](assignment-brief.md): each step says **what to do**, **what
the command does**, and **what to say**. The detailed procedures stay in the
linked guides; this file is for running the show.

Replace `A` and `B` with your names and `ELASTIC_IP` with the instance address.
Status of each requirement is in the [coverage tracker](project-plan.md#assignment-coverage-tracker).

## Rules from the brief to keep in mind

- At most **60 minutes**, starting from a **brand-new instance**, including SSH
  keys, security group and connection. Rehearse on a different instance.
- **Both** students are visible and heard. The terminal font must be readable.
- **Explain the commands** you run and **why** you chose each solution.
- Show basic terminal work **by hand** (step 5 opens the Nginx site in nano).
  Prepared code is allowed; a demo that is only `bash setup.sh` is not enough.
- Watch the recording afterwards, check the link, then **stop the instances**.
  An open HTTP port exposes the instance.

## Before you press record

- [ ] The code is merged to `main` and pushed. `git log -1 --oneline` noted.
- [ ] Each student has their own SSH key pair. Know both public IPs.
- [ ] Discord webhook URL ready to paste (never show it on screen).
- [ ] Domain registered and ready to point at the Elastic IP (VG2).
- [ ] Terminal font enlarged, unrelated tabs and notifications closed.
- [ ] This guide open on a second screen. Decide who says which part.

Never show `.env`, tokens, passwords, webhook URLs or private keys on screen.
Copy a token privately (for example in a second, unrecorded window).

## Time plan

| # | Part | Requirement | Speaker | Minutes |
|---|---|---|---|---:|
| 1 | Introduction and architecture | — | A + B | 3 |
| 2 | Launch the EC2 instance | G1 | A | 7 |
| 3 | Connect over SSH from both computers | G2 | A + B | 4 |
| 4 | Clone, copy setup with SCP, run setup | G3, G4 | B | 12 |
| 5 | Verify, Nginx by hand, public Swagger | G7, G8 | A | 6 |
| 6 | systemd and the database connection | G7, G9 | B | 4 |
| 7 | Cron backup and restore | G5 | A | 6 |
| 8 | Discord alert | G6 | B | 4 |
| 9 | Docker Compose and persistence | VG1 | A | 7 |
| 10 | Domain and HTTPS | VG2 | B | 5 |
| 11 | Wrap-up and shutdown | — | A + B | 2 |

Setup in step 4 takes several minutes. Use that time to talk (the talking
points below are written for it).

---

## 1. Introduction (3 min)

**Say:**
- "ServerWatch monitors one Ubuntu server. A collector measures CPU, memory and
  disk every five seconds and sends them to a FastAPI API, which stores them in
  PostgreSQL. A React dashboard shows them, and we can open incidents."
- "We deploy it twice on the same EC2 host: natively with systemd and Nginx for
  the G criteria, and with Docker Compose for VG."
- "The API has three separate tokens: reader, collector and admin. Each process
  gets only the credential it needs."

```
Browser ──► Nginx (:80/:443) ──► FastAPI (127.0.0.1:8000) ──► PostgreSQL (loopback)
                                      ▲
                     collector (systemd, every 5 s)
```

## 2. Launch the EC2 instance — G1 (7 min)

In the AWS console ([full steps](ec2-manual-setup.md#2-launch-a-fresh-ubuntu-ec2-instance-aws-console)):

1. **Launch instance**, name it, choose **Ubuntu 24.04 LTS** and a free-tier eligible type.
2. Create or select the key pair for the first `ubuntu` login.
3. Security group: **SSH 22** from A's IP `/32` and B's IP `/32` only.
4. Launch, wait for the status checks, then allocate and associate an **Elastic IP**.

**Say:**
- "Ubuntu LTS gets security updates for years, and our scripts target it."
- "We only open SSH, and only from our own addresses. PostgreSQL 5432 and the
  API's 8000 are never opened. HTTP 80 is added once Nginx is in place."
- "The Elastic IP keeps the address fixed when the instance restarts, which the
  domain needs later."

## 3. SSH from both computers — G2 (4 min)

A connects first:

```bash
chmod 400 ~/keys/initial-ec2-key.pem          # SSH refuses keys others can read
ssh -i ~/keys/initial-ec2-key.pem ubuntu@ELASTIC_IP
```

B gets an own account in step 4 (`SERVERWATCH_JUNIOR_USER`) and logs in with
B's own key after the account exists ([details](ubuntu-accounts.md#give-each-student-ssh-access)):

```bash
sudo install -d -o b -g b -m 700 /home/b/.ssh
sudo -u b nano /home/b/.ssh/authorized_keys     # paste B's PUBLIC key by hand
sudo chmod 600 /home/b/.ssh/authorized_keys
```

Then on B's computer: `ssh -i ~/.ssh/b_key b@ELASTIC_IP` and `id`.

**Say:**
- "Each of us has our own key pair. Private keys never leave our computers;
  the server only gets the public key."
- "`id` shows B's groups. B is a junior developer and can write to dev but only
  read prod."

## 4. Clone, SCP and setup — G3, G4 (12 min)

On EC2 as `ubuntu`:

```bash
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/EmirU116/server-api.git ~/serverwatch
cd ~/serverwatch && git log -1 --oneline
```

On your computer, from the checkout, send the setup script:

```bash
scp -i ~/keys/initial-ec2-key.pem setup.sh ubuntu@ELASTIC_IP:~/setup.sh
```

Save the Discord webhook privately ([commands](discord-alerts.md#configure-the-alert-discord-bash-systemd);
the prompt hides the input), then run setup on EC2:

```bash
export SERVERWATCH_SENIOR_USER=a
export SERVERWATCH_JUNIOR_USER=b
export SERVERWATCH_DISCORD_WEBHOOK_FILE="$HOME/.config/serverwatch-alerts/discord-webhook"
SERVERWATCH_PROJECT_DIR="$HOME/serverwatch" bash ~/setup.sh ELASTIC_IP
```

| Command | What it does |
|---|---|
| `git clone … ~/serverwatch` | Puts the code in the `ubuntu` user's home, owned by that user |
| `scp` | Copies a file to the server over the same encrypted SSH connection |
| `SERVERWATCH_PROJECT_DIR=…` | Tells the copied script where the cloned project is |
| `bash setup.sh ELASTIC_IP` | Installs packages, PostgreSQL, migrations, the API and collector services, React and Nginx, Cron backups, Docker, the student accounts, the Discord timer and the `sw-*` aliases |

**Say (while setup runs):**
- "We clone into the home folder of the user that runs the services. That user
  owns the files, so no service needs root, and `git pull` works without sudo."
- "The script is safe to rerun: it keeps existing passwords and data. That is
  also how we update the server."
- "It generates every password and token itself, once, as files only that user
  can read (mode 600). Nothing secret is in Git."
- "We create two accounts with different rights: senior can write to prod,
  junior only to dev. That is least privilege, enforced with groups and ACLs."
- "The aliases `sw-status`, `sw-logs` and `sw-timers` save typing during
  operations; `sw-help` lists them."

## 5. Verify, Nginx by hand, public Swagger — G7, G8 (6 min)

```bash
bash verify.sh ELASTIC_IP          # read-only checks; expect 8 passed, 0 failed
```

Now the manual part. Open the Nginx site the script installed:

```bash
cd /etc/nginx/sites-enabled
ls -l
sudo nano serverwatch.conf
sudo nginx -t                      # check the syntax before applying
sudo systemctl reload nginx        # apply without dropping connections
```

**Explain the file:** `listen 80` is the public port; `root` serves the built
React files; the `location` for `/api`, `/docs` and `/openapi.json` forwards to
`proxy_pass http://127.0.0.1:8000`, the API on loopback.

In AWS, add **HTTP 80** to the security group. On your computer, open:
`http://ELASTIC_IP/`, `http://ELASTIC_IP/docs`, `http://ELASTIC_IP/api/v1/health?server_id=1`.

**Say:**
- "Nginx is a reverse proxy: the only public entry point. The API itself
  listens only on 127.0.0.1, so it can't be reached from the internet directly."
- "`nginx -t` first, because a broken config would take the site down on reload."
- "Over plain HTTP the dashboard runs in demo mode. Live data needs a token,
  and tokens are only accepted over HTTPS, which we add in VG2."

## 6. systemd and the database — G7, G9 (4 min)

```bash
sw-status                                   # API and collector: active (running)
systemctl cat serverwatch-api               # the unit file
sudo ss -ltnp | grep -E ':5432|:8000'       # both bound to 127.0.0.1 only
```

**Say:**
- "systemd starts the API at boot and restarts it if it crashes. Same for the
  collector."
- "The API connects to PostgreSQL on loopback with its own limited database
  user. Tables are created by Alembic migrations, never by the app at start."
- "The health endpoint checks the database for real, which is why it returned
  `up` in the browser."

## 7. Cron backup and restore — G5 (6 min)

```bash
sudo cat /etc/cron.d/serverwatch-backup     # daily at 03:15
sudoedit /etc/cron.d/serverwatch-backup     # set it to the next minute for the demo
sudo journalctl -t serverwatch-backup -n 10 --no-pager
sudo ls -lt /var/backups/serverwatch
```

Then run the restore block from the [EC2 guide](ec2-manual-setup.md#verify-cron-backups-and-restore-g5)
into a separate database and show the row counts. Restore the 03:15 schedule.

**Say:**
- "Cron runs a daily `pg_dump` and saves the last 24 hours of service logs."
- "A backup only counts if you can restore it, so we restore into a separate
  database and count the rows."
- "These backups live on the same disk. In production we would copy them off
  the server, for example with SCP or to S3."

## 8. Discord alert — G6 (4 min)

```bash
sw-timers                                   # runs about once a minute
df -h /                                     # note the current usage, e.g. 31%
bash infrastructure/bootstrap/setup_discord_alerts.sh \
  "$HOME/.config/serverwatch-alerts/discord-webhook" 25
```

Wait for the message in Discord, then put the normal threshold back with the
same command and `90`.

**Say:**
- "A systemd timer checks disk usage every minute and posts to Discord when it
  crosses the threshold. We lower the threshold to trigger it safely."
- "It sends one alert per breach, not one per minute, and rearms when usage
  drops again."
- "We used a systemd timer instead of Cron here because systemd can hand the
  webhook to only this service, as a protected credential."

## 9. Docker Compose and persistence — VG1 (7 min)

```bash
cd ~/serverwatch
bash scripts/deployment/compose_host.sh start          # build images, start db → migrate → api → web
bash scripts/deployment/compose_host.sh ps -a          # db/api/web healthy, migrate Exited (0)
bash scripts/deployment/compose_host.sh collect        # Ctrl+C after ~20 s
bash scripts/deployment/compose_host.sh exec db psql -U postgres -d serverwatch -c "SELECT count(*) FROM metrics;"
bash scripts/deployment/compose_host.sh down           # containers and networks removed, volume kept
bash scripts/deployment/compose_host.sh up -d --wait
bash scripts/deployment/compose_host.sh exec db psql -U postgres -d serverwatch -c "SELECT count(*) FROM metrics;"
```

The two counts must match.

| Term | One line |
|---|---|
| Dockerfile | The recipe for an image |
| Image | The built, read-only package |
| Container | A running copy of an image; disposable |
| Volume | Storage outside the container; `postgres_data` keeps the database |
| Compose | One file that starts all services in order, with networks and secrets |

**Say:**
- "Four services: PostgreSQL, a one-time migration job, the API and an Nginx
  web container. `migrate` exiting with 0 is success, not a crash."
- "Compose gives each service a name on a private network: the API reaches the
  database at `db`. The database network is internal and publishes no port."
- "Containers are disposable; the volume isn't. The count is the same after
  recreating everything, so the data lives in the volume."
- "The native deployment is still running beside it. This is the same app,
  packaged so it runs the same way on any machine with Docker."

## 10. Domain and HTTPS — VG2 (5 min)

> Not implemented yet. Fill in the exact commands once the Certbot step is
> built and rehearsed.

Planned flow: the domain's DNS `A` record points to the Elastic IP, Nginx gets
the domain as `server_name`, Certbot issues the certificate and adds the HTTPS
configuration, then `https://DOMAIN/docs` loads and `certbot renew --dry-run`
passes. Add **HTTPS 443** to the security group.

**Say:**
- "Certbot gets a free certificate from Let's Encrypt and proves we control the
  domain. It renews automatically."
- "With HTTPS we can connect the dashboard with a real token and edit an
  incident live."

## 11. Wrap-up (2 min)

**Say:** what each of you built, one thing you would do next (off-server
backups, AWS Secrets Manager, automated deploys), then stop the recording.

Afterwards: watch the video, check the link, **stop or terminate the instance**
and release the Elastic IP.

## Likely questions

| Question | Short answer |
|---|---|
| Why not run as root? | A bug or break-in would control the whole server. Services run as a normal user. |
| Why loopback for the API and database? | Only Nginx is public; everything else is unreachable from outside. |
| Why three tokens? | Least privilege: the collector can't read or delete, a reader can't write. |
| Why migrations instead of creating tables at start? | Schema changes are versioned, reviewable and can be rolled back. |
| Native or Docker — which is better? | Docker is more portable and reproducible; native shows what Docker automates. |
| What if the server dies? | Backups are on the same disk today; next step is copying them off the host. |
