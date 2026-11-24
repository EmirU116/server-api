#!/usr/bin/env bash
# Install packages, PostgreSQL, the API/collector services and Cron backups.
# Called by the root setup.sh, which then publishes the web tier and verifies.
# Run as the SSH user, not sudo bash.
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
    echo "Usage: bash setup_ubuntu_monitoring.sh [project-directory]"
    echo "Ubuntu 24.04+, sudo access, cloned repository, and free port 8000 required."
    echo "Installs packages, local PostgreSQL, private credentials, migrations, API and"
    echo "collector services, and the Cron backup. Normally run through setup.sh."
    echo "Reruns preserve credentials/data. Does not configure Nginx, HTTPS or AWS resources."
    exit 0
fi
if (( $# > 1 )) || [[ "${1:-}" == --* ]]; then
    echo "[FAIL] Supply at most one project directory; use --help." >&2
    exit 1
fi
trap 'echo "[FAIL] Setup stopped at line $LINENO. Fix the reported issue and rerun." >&2' ERR
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
project_dir=$(realpath -- "${1:-$script_dir/../..}")
config_dir="$HOME/.config/serverwatch-monitoring"
run_user=$(id -un)

if (( EUID == 0 )); then
    echo "[FAIL] Run as your normal SSH user; this script uses sudo where needed."
    exit 1
fi
if [[ ! "$project_dir" =~ ^/[a-zA-Z0-9_./-]+$ || ! "$config_dir" =~ ^/[a-zA-Z0-9_./-]+$ ]]; then
    echo "[FAIL] Project/home paths must contain no spaces or special characters."
    exit 1
fi
source /etc/os-release
if [[ "$ID" != ubuntu || "${VERSION_ID%%.*}" -lt 24 || -f /.dockerenv || -f /run/.containerenv ]] ||
    [[ "$(uname -r)" == *[Mm]icrosoft* ]] || [[ ! -d /run/systemd/system ]]; then
    echo "[FAIL] Native Ubuntu 24.04+ with running systemd is required; no WSL/containers."
    exit 1
fi
if [[ ! -f "$project_dir/backend/requirements.txt" || ! -f "$project_dir/scripts/monitoring/collect_local.py" ]]; then
    echo "[FAIL] Clone the current project first."
    exit 1
fi
# Refuse to replace another checkout's managed services or an older smoke-test
# deployment. Never stop arbitrary processes simply to make a port available.
for service in serverwatch-api serverwatch-collector; do
    fragment=$(systemctl show "$service.service" -p FragmentPath --value 2>/dev/null || true)
    if [[ -n "$fragment" ]]; then
        directory=$(systemctl show "$service.service" -p WorkingDirectory --value)
        service_user=$(systemctl show "$service.service" -p User --value)
        if [[ "$fragment" != "/etc/systemd/system/$service.service" ||
              "$directory" != "$project_dir" || "$service_user" != "$run_user" ]]; then
            echo "[FAIL] $service is already installed for a different setup."
            exit 1
        fi
    fi
done

packages=(python3 python3-venv python3-pip postgresql postgresql-client iproute2
    git nginx curl cron ca-certificates xz-utils acl)
# Keep Docker's own packages when they are installed; otherwise use Ubuntu's.
if dpkg-query -W -f='${db:Status-Status}' docker-ce 2>/dev/null | grep -qx installed; then
    docker compose version >/dev/null 2>&1 || packages+=(docker-compose-plugin)
    docker buildx version >/dev/null 2>&1 || packages+=(docker-buildx-plugin)
else
    docker compose version >/dev/null 2>&1 || packages+=(docker.io docker-compose-v2)
    docker buildx version >/dev/null 2>&1 || packages+=(docker-buildx)
fi
echo "[SETUP] Installing Ubuntu packages: ${packages[*]}"
sudo apt-get update
sudo apt-get install -y "${packages[@]}"
sudo systemctl enable --now docker.service
docker compose version
docker buildx version
python3 -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ required"'
if ! systemctl is-active --quiet serverwatch-api.service; then
    python3 - <<'CHECK_PORT'
import socket
with socket.socket() as listener:
    try:
        listener.bind(("127.0.0.1", 8000))
    except OSError:
        raise SystemExit("[FAIL] Port 8000 is occupied; stop the existing API yourself.")
CHECK_PORT
fi
if [[ ! -d "$project_dir/.venv" ]]; then python3 -m venv "$project_dir/.venv"; fi
python="$project_dir/.venv/bin/python"
"$python" -m pip install -r "$project_dir/backend/requirements.txt"
"$python" -m pip check

umask 077
helper="$project_dir/scripts/setup/configure_ubuntu.py"
"$python" "$helper" prepare "$config_dir"
sudo systemctl enable --now postgresql.service
# psql receives a SCRAM verifier via stdin, never a clear password in arguments.
# Suppress raw SQL errors because they might include that sensitive verifier.
if ! "$python" "$helper" database-sql "$config_dir" |
    sudo -u postgres psql -X -q -v ON_ERROR_STOP=1 \
        -h /var/run/postgresql -p 5432 -U postgres -d postgres > /dev/null 2>&1; then
    echo "[FAIL] Could not provision local PostgreSQL. Existing roles/passwords were not reset."
    exit 1
fi
# No ambient shell setting may redirect the migration away from this local DB.
env -i HOME="$HOME" PATH="$PATH" "$python" "$project_dir/backend/migrate.py" --env-file "$config_dir/api.env"

echo "[SETUP] Installing API and collector systemd services."
work_dir=$(mktemp -d)
trap 'rm -rf -- "$work_dir"' EXIT
for service in serverwatch-api serverwatch-collector; do
    sed -e "s|@PROJECT_DIR@|$project_dir|g" \
        -e "s|@CONFIG_DIR@|$config_dir|g" \
        -e "s|@RUN_USER@|$run_user|g" \
        "$project_dir/infrastructure/systemd/$service.service" > "$work_dir/$service.service"
    sudo install -m 644 "$work_dir/$service.service" "/etc/systemd/system/$service.service"
done
sudo systemctl daemon-reload
sudo systemctl enable serverwatch-api.service serverwatch-collector.service
sudo systemctl restart serverwatch-api.service
sudo systemctl restart serverwatch-collector.service
echo "[SETUP] Installing the native PostgreSQL and service log backup schedule."
sudo install -o root -g root -m 755 -- "$project_dir/scripts/backup/backup_native.sh" /usr/local/sbin/serverwatch-backup
sudo install -o root -g root -m 644 -- "$project_dir/infrastructure/cron/serverwatch-backup" /etc/cron.d/serverwatch-backup
sudo systemctl enable --now cron.service
echo "[OK] Monitoring is running; services start at boot. Credentials were not printed."
