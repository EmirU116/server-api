#!/usr/bin/env bash
# Run Compose with the host-owned settings file kept outside the checkout.
#   start    create missing settings and secrets, then start the stack
#   prepare  create missing secrets only
#   collect  send this host's metrics to the Compose API until Ctrl+C
#   anything else is passed to docker compose (for example: ps, logs, down)
set -euo pipefail
project="$HOME/serverwatch"
config="$HOME/.config/serverwatch-delivery/compose.env"
fail() { echo "[FAIL] $*" >&2; exit 1; }

if [[ "${1:-}" == --help && $# == 1 ]]; then
    echo "Usage: bash scripts/deployment/compose_host.sh start | prepare | collect | COMPOSE_COMMAND"
    echo "start creates missing configuration and starts the stack."
    echo "collect records host metrics until stopped with Ctrl+C."
    exit 0
fi

create_default_config() {
    docker info --format '{{.ServerVersion}}' >/dev/null 2>&1 ||
        fail 'Cannot reach Docker. Check that Docker is running and this account has access.'
    [[ -e "$config" ]] && return
    (
        umask 077
        mkdir -p -- "$(dirname -- "$config")"
        set -o noclobber
        printf '%s\n' 'SERVERWATCH_WEB_PORT=8080' \
            'SERVERWATCH_COMPOSE_SECRETS="${HOME}/.config/serverwatch-compose/secrets"' > "$config"
    )
}

# The secrets directory is wherever Compose resolves the db_password secret.
secret_dir() {
    "${compose[@]}" config --format json | python3 -c '
import json, sys
from pathlib import Path
print(Path(json.load(sys.stdin)["secrets"]["db_password"]["file"]).parent)
'
}

collect() {
    local endpoint port collector_env python
    endpoint=$("${compose[@]}" port web 80)
    [[ "$endpoint" =~ ^127\.0\.0\.1:([0-9]+)$ ]] ||
        fail 'Start Compose with its web port bound to 127.0.0.1 before collecting.'
    port=${BASH_REMATCH[1]}
    collector_env="$(secret_dir)/collector.env"
    [[ -r "$collector_env" ]] ||
        fail 'Run compose_host.sh prepare to create the collector configuration.'
    python="$project/.venv/bin/python"
    [[ -x "$python" ]] || fail 'Run setup.sh first to create the project virtual environment.'
    # The collector must use only the Compose credential, never a native one.
    unset SERVERWATCH_COLLECTOR_TOKEN SERVERWATCH_COLLECTOR_TOKEN_FILE
    exec "$python" "$project/scripts/monitoring/collect_local.py" \
        --env-file "$collector_env" --api-port "$port"
}

action=${1:-}
[[ "$action" == start && $# == 1 ]] && create_default_config
[[ -f "$config" && -r "$config" ]] || fail "Create the Compose operator's configuration at $config."

# Shell exports would otherwise override the explicit host env file.
unset SERVERWATCH_WEB_PORT SERVERWATCH_COMPOSE_SECRETS
export SERVERWATCH_WEB_BIND=127.0.0.1
export SERVERWATCH_RUNTIME_UID="$(id -u)" SERVERWATCH_RUNTIME_GID="$(id -g)"
compose=(docker compose --project-directory "$project" --project-name serverwatch \
    --env-file "$config" --file "$project/compose.yaml")

case "$action:$#" in
    prepare:1)
        exec bash "$project/scripts/setup/prepare_compose.sh" "$(secret_dir)"
        ;;
    start:1)
        bash "$project/scripts/setup/prepare_compose.sh" "$(secret_dir)"
        "${compose[@]}" up -d --build --wait
        exec "${compose[@]}" ps -a
        ;;
    collect:1)
        collect
        ;;
    *)
        exec "${compose[@]}" "$@"
        ;;
esac
