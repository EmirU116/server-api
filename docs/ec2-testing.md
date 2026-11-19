# Native EC2 setup and verification (Bash, Ubuntu, systemd)

For local PostgreSQL, migrations, and continuous host metrics, use the newer
[Ubuntu monitoring setup](ubuntu-monitoring.md). This document describes the
older health/server smoke-test service, which intentionally has no database.

These scripts prepare and test the current health/server APIs on an existing
Ubuntu EC2 instance. They do not create AWS resources or complete the full course
deployment. Use Ubuntu 24.04 or newer, Python 3.11+, and a normal SSH user with
sudo access. Clone the project into a directory owned by that user first.

## Connect and prepare

Allow inbound SSH port 22 from your IP in the instance's security group. Keep
your private key on your computer. No inbound API port is needed: the service
listens only on `127.0.0.1:8000` and verification runs over SSH on the instance.

From your computer, replace the example paths and address:

```bash
ssh -i /path/to/key.pem ubuntu@EC2_PUBLIC_IP
```

On the instance, clone a revision containing the scripts and current API code:

```bash
sudo apt-get update
sudo apt-get install -y git
git clone YOUR_REPOSITORY_URL "$HOME/serverwatch-test"
cd "$HOME/serverwatch-test"
bash infrastructure/bootstrap/setup_ec2.sh
bash scripts/verification/verify_ec2.sh
```

New local files must be committed/pushed by you or transferred before EC2 can
use them. Never copy a local `.env`, private key, or existing `.venv` into the
clone. Create the virtual environment on EC2.

If demonstrating transfer of the bootstrap script with SCP, from your computer:

```bash
scp -i /path/to/key.pem infrastructure/bootstrap/setup_ec2.sh ubuntu@EC2_PUBLIC_IP:~/setup_ec2.sh
```

After cloning the repository on the instance, run the transferred script with
the clone's absolute path:

```bash
bash "$HOME/setup_ec2.sh" "$HOME/serverwatch-test"
bash "$HOME/serverwatch-test/scripts/verification/verify_ec2.sh" "$HOME/serverwatch-test"
```

Run setup as the normal SSH user, **not** `sudo bash ...`; it uses sudo only for
package and service administration. Project/home paths must not contain spaces
or special characters. Port 8000 must be available before starting this service.

## What setup does

- Installs Python, pip, venv, Git, and curl using Ubuntu packages.
- Creates `.venv`, installs pinned runtime dependencies, and checks consistency.
- Generates a reader token once in
  `~/.config/serverwatch-ec2-test/reader_token` with mode `600`; the directory is
  mode `700`. The token is never printed. Reruns preserve it.
- Writes a private environment file for numeric server ID `1`, display name
  `ServerWatch EC2 test`, production mode, and the token file location.
- Installs the dedicated `serverwatch-ec2-test.service`, enables it at boot,
  and restarts it as the SSH user on localhost port 8000. Production mode disables
  Swagger/ReDoc/OpenAPI. The systemd template is under `infrastructure/systemd/`.

Rerunning setup reapplies dependencies, the test environment file, and the test
service definition. This is a dedicated testing configuration; do not point it
at a separately managed production service. It does not update an existing Git
checkout. No real credentials are included in source control.

## Verification and feedback

Run verification as the same user who ran setup. The script is read-only except
for private temporary response files, which it removes on exit. It checks:

| Check | Expected result |
| --- | --- |
| Host and tools | Native Ubuntu, Python/curl/systemctl/stat installed |
| Python environment | Runtime imports and dependency consistency pass |
| Test service | Enabled, active, API reachable within a bounded startup wait |
| Reader token | Exists, owned by current user, mode `600`, generated format |
| Server without token | `401` |
| Server default and explicit ID `1` | `200`, metadata matches the host |
| Negative ID on health/server | `400` |
| Unknown ID `2` on health/server | `404` |
| Unexpected server query parameter | `422` |
| Health for ID `1` | Structured `503`: server up, database down |

`[PASS]` confirms an individual check. `[FAIL]` identifies a missing or incorrect
component. `[WARN]` describes an expected limitation or skipped check. The final
summary counts each category; exit status is `0` when no checks failed and `1`
otherwise. The current database-related health warning does not fail verification.
Once persistence is implemented, update that expected health state.

If startup fails, inspect locally:

```bash
sudo systemctl status serverwatch-ec2-test.service --no-pager
sudo journalctl -u serverwatch-ec2-test.service -n 50 --no-pager
```

To stop testing and prevent automatic startup:

```bash
sudo systemctl disable --now serverwatch-ec2-test.service
```

## Limits and local validation

These scripts do not configure or verify AWS security groups, public SSH access,
Elastic IPs, Nginx, HTTPS, PostgreSQL, migrations, monitoring, backups, alerts,
Docker, or frontend deployment. They cannot prove the instance is EC2 merely by
reading host metadata. The course recording still requires a fresh instance.

Local checks for contributors:

```bash
bash -n infrastructure/bootstrap/setup_ec2.sh
bash -n scripts/verification/verify_ec2.sh
.venv/bin/python -m pytest tests/test_ec2_verification.py -q
```

The verification tests simulate systemd and HTTP success/failure with dummy
credentials and temporary files; they do not provision a machine. A real native
Ubuntu EC2 run is still required to verify package installation and service startup.
