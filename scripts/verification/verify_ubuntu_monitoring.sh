#!/usr/bin/env bash
# Read-only diagnostics: observe the collector's writes; never create test data.
set -euo pipefail
if [[ "${1:-}" == "--help" ]]; then
    echo "Usage: bash verify_ubuntu_monitoring.sh [project-directory]"
    echo "Run as the setup user. Reports PASS/FAIL and waits up to 30s for fresh stored metrics."
    echo "No credentials are printed; no records, services or settings are changed."
    exit 0
fi
if (( $# > 1 )) || [[ "${1:-}" == --* ]]; then
    echo "[FAIL] Supply at most one project directory; use --help." >&2
    exit 1
fi
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
project_dir=$(realpath -- "${1:-$script_dir/../..}")
passed=0
failed=0
pass() { echo "[PASS] $*"; passed=$((passed + 1)); }
fail() { echo "[FAIL] $*"; failed=$((failed + 1)); }
source /etc/os-release
if [[ "$ID" == ubuntu && "${VERSION_ID%%.*}" -ge 24 && ! -f /.dockerenv && ! -f /run/.containerenv ]] &&
    [[ "$(uname -r)" != *[Mm]icrosoft* && -d /run/systemd/system ]]; then
    pass "Native Ubuntu host with systemd"
else
    fail "Native Ubuntu 24.04+ with systemd required"
fi
for command in systemctl ss; do
    if command -v "$command" >/dev/null; then pass "$command available"; else fail "$command missing"; fi
done
if command -v systemctl >/dev/null; then
    for service in postgresql serverwatch-api serverwatch-collector; do
        if systemctl is-enabled --quiet "$service.service" && systemctl is-active --quiet "$service.service"; then
            pass "$service enabled and active"
        else
            fail "$service inactive or not enabled; inspect systemctl status $service"
        fi
    done
fi
python="$project_dir/.venv/bin/python"
if [[ -x "$python" ]] && "$python" -m pip check > /dev/null 2>&1; then
    pass "Python environment and dependencies"
    if "$python" "$project_dir/scripts/verification/check_ubuntu_monitoring.py" "$HOME/.config/serverwatch-monitoring"; then
        pass "Private configuration, schema, API, host identity and fresh persisted metrics"
    else
        fail "Monitoring checks incomplete; follow the diagnostic above"
    fi
else
    fail "Python environment missing or dependencies inconsistent; run setup"
fi
echo "[SUMMARY] $passed passed, $failed failed."
echo "[INFO] Public access, React, Nginx, HTTPS, AWS settings, backups and alerts are not checked."
(( failed == 0 ))
