#!/usr/bin/env bash
# Read-only checks of the native test deployment. Never print reader credentials.
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
    echo "Usage: bash verify_ec2.sh [project-directory]"
    echo "Run as the same SSH user who ran setup_ec2.sh. Exit 1 means a failed check."
    exit 0
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(realpath -- "${1:-$script_dir/../..}")"
config_dir="$HOME/.config/serverwatch-ec2-test"
base_url="http://127.0.0.1:8000/api/v1"
passed=0
failed=0
warnings=0

pass() { echo "[PASS] $*"; passed=$((passed + 1)); }
fail() { echo "[FAIL] $*"; failed=$((failed + 1)); }
warn() { echo "[WARN] $*"; warnings=$((warnings + 1)); }

for command in python3 curl systemctl stat; do
    if command -v "$command" > /dev/null; then
        pass "$command is installed"
    else
        fail "$command is missing; run setup first"
    fi
done
if (( failed > 0 )); then
    echo "[SUMMARY] $passed passed, $failed failed, $warnings warnings. API checks skipped."
    exit 1
fi

if [[ -f /etc/os-release ]]; then
    source /etc/os-release
    if [[ "$ID" == "ubuntu" ]]; then pass "Ubuntu host"; else fail "Host is not Ubuntu"; fi
else
    fail "Operating system identification is missing"
fi
if [[ -f /.dockerenv || -f /run/.containerenv ]]; then
    fail "Container detected; native host deployment is required"
fi
if [[ -x "$project_dir/.venv/bin/python" ]]; then
    if "$project_dir/.venv/bin/python" -m pip check > /dev/null 2>&1 &&
        "$project_dir/.venv/bin/python" -c 'import fastapi, uvicorn, pydantic_settings' > /dev/null 2>&1; then
        pass "Python runtime dependencies are available and consistent"
    else
        fail "Python runtime dependencies are missing or inconsistent"
    fi
else
    fail "Project virtual environment is missing"
fi
if systemctl is-enabled --quiet serverwatch-ec2-test.service 2>/dev/null; then
    pass "Test service is enabled for boot"
else
    fail "Test service is not enabled"
fi

# Allow a newly restarted service a short, bounded startup window.
ready=false
for _ in {1..10}; do
    # Any HTTP status proves Uvicorn is listening; a refused connection does not.
    if curl --silent --max-time 1 "$base_url/health?server_id=0" > /dev/null 2>&1; then
        ready=true
        break
    fi
    sleep 1
done
if systemctl is-active --quiet serverwatch-ec2-test.service; then
    pass "Test service is active"
else
    fail "Test service is inactive; inspect sudo journalctl -u serverwatch-ec2-test"
fi
if [[ "$ready" != true ]]; then
    fail "API is unreachable on localhost:8000"
    echo "[SUMMARY] $passed passed, $failed failed, $warnings warnings."
    exit 1
fi

umask 077
work_dir="$(mktemp -d)"
trap 'rm -rf -- "$work_dir"' EXIT
token_file="$config_dir/reader_token"
auth_ready=false
if [[ -r "$token_file" && -s "$token_file" ]]; then
    if [[ "$(stat -c '%a' "$token_file")" == "600" && "$(stat -c '%u' "$token_file")" == "$EUID" ]]; then
        pass "Reader token file is private and owned by this user"
        # The credential goes through stdin, never through curl's process arguments.
        reader_token="$(< "$token_file")"
        if [[ "$reader_token" =~ ^[a-zA-Z0-9_-]+$ ]]; then
            auth_ready=true
        else
            fail "Reader token does not match setup's generated token format"
        fi
    else
        fail "Reader token needs mode 600 and ownership by the setup user"
    fi
else
    fail "Reader token is missing or unreadable; run as the setup user"
fi

check_http() {
    local label="$1" path="$2" expected="$3" authenticated="${4:-false}"
    local status
    if [[ "$authenticated" == true ]]; then
        status="$(printf 'header = "Authorization: Bearer %s"\n' "$reader_token" |
            curl --config - --silent --show-error --max-time 3 \
                --output "$work_dir/response.json" --write-out '%{http_code}' "$base_url$path")" || status=000
    else
        status="$(curl --silent --show-error --max-time 3 \
            --output "$work_dir/response.json" --write-out '%{http_code}' "$base_url$path")" || status=000
    fi
    if [[ "$status" == "$expected" ]]; then pass "$label (HTTP $status)"; else fail "$label: expected $expected, received $status"; fi
}

check_http "Server rejects missing authentication" "/server" 401
check_http "Health rejects negative IDs" "/health?server_id=-1" 400
check_http "Health rejects unregistered IDs" "/health?server_id=2" 404
check_http "Health reports unconfigured database" "/health?server_id=1" 503
if python3 - "$work_dir/response.json" <<'PY'
import json
import sys
try:
    with open(sys.argv[1]) as response_file:
        data = json.load(response_file)
    assert data["server_id"] == 1
    assert data["status"] == "unhealthy"
    assert data["checks"] == {"server": "up", "database": "down"}
except (OSError, ValueError, KeyError, TypeError, AssertionError):
    sys.exit(1)
PY
then
    warn "Database is not configured yet; the current structured health 503 is expected"
else
    fail "Health response does not match the current expected dependency state"
fi

if [[ "$auth_ready" == true ]]; then
    check_http "Server default selection" "/server" 200 true
    check_http "Server explicit selection" "/server?server_id=1" 200 true
    if PYTHONPATH="$project_dir/backend" "$project_dir/.venv/bin/python" - "$work_dir/response.json" <<'PY'
import json
import sys
from app.services.server import read_host_info
try:
    with open(sys.argv[1]) as response_file:
        data = json.load(response_file)
    assert data == {"id": 1, "name": "ServerWatch EC2 test", **read_host_info()}
except Exception:
    sys.exit(1)
PY
    then
        pass "Server response matches this host's identity and OS"
    else
        fail "Server response is incomplete or differs from this host"
    fi
    check_http "Server rejects negative IDs" "/server?server_id=-1" 400 true
    check_http "Server rejects unregistered IDs" "/server?server_id=2" 404 true
    check_http "Server rejects unknown parameters" "/server?verbose=true" 422 true
else
    warn "Authenticated server checks skipped because token setup is incomplete"
fi
unset reader_token

echo "[SUMMARY] $passed passed, $failed failed, $warnings warnings."
echo "[INFO] AWS security groups, SSH access, Nginx, HTTPS, PostgreSQL, backups, and alerts are not verified."
(( failed == 0 ))
