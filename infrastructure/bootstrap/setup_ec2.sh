#!/usr/bin/env bash
# Prepare a cloned repository on a native Ubuntu host for API smoke testing.
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
    echo "Usage: bash setup_ec2.sh [project-directory]"
    echo "Run as the normal Ubuntu SSH user, with sudo access. Clone the repo first."
    exit 0
fi

trap 'echo "[FAIL] Setup stopped at line $LINENO. Fix the error above and rerun." >&2' ERR

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(realpath -- "${1:-$script_dir/../..}")"
config_dir="$HOME/.config/serverwatch-ec2-test"
service_name="serverwatch-ec2-test"
run_user="$(id -un)"

if [[ "$EUID" -eq 0 ]]; then
    echo "[FAIL] Run as your normal SSH user, without sudo before this script."
    exit 1
fi

# Restrict generated systemd paths to avoid quoting and directive-injection issues.
if [[ ! "$project_dir" =~ ^/[a-zA-Z0-9_./-]+$ || ! "$config_dir" =~ ^/[a-zA-Z0-9_./-]+$ ]]; then
    echo "[FAIL] Project and home paths must contain no spaces or special characters."
    exit 1
fi
if [[ ! -f "$project_dir/backend/requirements.txt" ]]; then
    echo "[FAIL] Clone the project first, then supply its directory."
    exit 1
fi
if [[ ! -f /etc/os-release ]]; then
    echo "[FAIL] This setup supports native Ubuntu only."
    exit 1
fi
# /etc/os-release is the operating system's trusted identification file.
source /etc/os-release
if [[ "$ID" != "ubuntu" || -f /.dockerenv || -f /run/.containerenv ]]; then
    echo "[FAIL] Use a native Ubuntu EC2 instance, not a container."
    exit 1
fi
if [[ ! -d /run/systemd/system ]]; then
    echo "[FAIL] A running systemd installation is required."
    exit 1
fi

echo "[SETUP] Installing Python, venv, pip, Git, and curl."
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git curl
python3 -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ required; use Ubuntu 24.04 or newer"'

echo "[SETUP] Creating the Python environment and installing runtime dependencies."
if [[ ! -d "$project_dir/.venv" ]]; then
    python3 -m venv "$project_dir/.venv"
fi
"$project_dir/.venv/bin/python" -m pip install -r "$project_dir/backend/requirements.txt"
"$project_dir/.venv/bin/python" -m pip check

# These runtime files stay outside the repository. Reruns preserve the token.
umask 077
mkdir -p "$config_dir"
chmod 700 "$config_dir"
if [[ ! -e "$config_dir/reader_token" ]]; then
    python3 -c 'import secrets; print(secrets.token_urlsafe(32))' > "$config_dir/reader_token"
fi
chmod 600 "$config_dir/reader_token"
cat > "$config_dir/serverwatch.env" <<EOF
SERVERWATCH_ENVIRONMENT=production
SERVERWATCH_SERVER_ID=1
SERVERWATCH_SERVER_NAME="ServerWatch EC2 test"
SERVERWATCH_READER_TOKEN_FILE=$config_dir/reader_token
PYTHONDONTWRITEBYTECODE=1
EOF

# Only this dedicated test unit is managed; no firewall or AWS settings change.
unit_file="$(mktemp)"
trap 'rm -f -- "$unit_file"' EXIT
sed \
    -e "s|@PROJECT_DIR@|$project_dir|g" \
    -e "s|@CONFIG_DIR@|$config_dir|g" \
    -e "s|@RUN_USER@|$run_user|g" \
    "$project_dir/infrastructure/systemd/serverwatch-ec2-test.service" > "$unit_file"
sudo install -m 644 "$unit_file" "/etc/systemd/system/$service_name.service"
sudo systemctl daemon-reload
sudo systemctl enable "$service_name.service"
sudo systemctl restart "$service_name.service"

echo "[OK] Setup completed. API listens on 127.0.0.1:8000."
echo "[INFO] Reader token is stored privately and has not been printed."
echo "[INFO] Run the verification script next:"
echo "bash $project_dir/scripts/verification/verify_ec2.sh $project_dir"
