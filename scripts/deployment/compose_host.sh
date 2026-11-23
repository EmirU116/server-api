#!/usr/bin/env bash
# Share host settings between manual Compose commands and approved releases.
set -euo pipefail
project="$HOME/serverwatch"
config="$HOME/.config/serverwatch-delivery/compose.env"
action=${1:-}
if [[ "$action" == --help && $# == 1 ]]; then
    echo "Usage: bash scripts/deployment/compose_host.sh start | collect | COMPOSE_COMMAND"
    echo "start creates missing configuration and starts the stack."
    echo "collect records host metrics until stopped with Ctrl+C."
    exit 0
fi
if [[ "$action" == start && $# == 1 ]]; then
    if ! docker info --format '{{.ServerVersion}}' >/dev/null 2>&1; then
        echo "[FAIL] Cannot reach Docker. Check that Docker is running and this account has access." >&2
        exit 1
    fi
    if [[ ! -e "$config" ]]; then
        (
            umask 077
            mkdir -p -- "$(dirname -- "$config")"
            set -o noclobber
            printf '%s\n' 'SERVERWATCH_WEB_PORT=8080' \
                'SERVERWATCH_COMPOSE_SECRETS="${HOME}/.config/serverwatch-compose/secrets"' > "$config"
        )
    fi
fi
if [[ ! -f "$config" || ! -r "$config" ]]; then
    echo "[FAIL] Create the Compose operator's configuration at $config." >&2
    exit 1
fi

# Shell exports would otherwise override the explicit host env file.
unset SERVERWATCH_WEB_PORT SERVERWATCH_COMPOSE_SECRETS
export SERVERWATCH_WEB_BIND=127.0.0.1
export SERVERWATCH_RUNTIME_UID="$(id -u)" SERVERWATCH_RUNTIME_GID="$(id -g)"
compose=(docker compose --project-directory "$project" --project-name serverwatch --env-file "$config")
if [[ "$action" != --file ]]; then
    compose+=(--file "$project/compose.yaml")
fi
if [[ $# == 1 && ( "$action" == prepare || "$action" == start || "$action" == collect ) ]]; then
    secret_dir=$("${compose[@]}" config --format json | python3 -c '
import json
from pathlib import Path
import sys

print(Path(json.load(sys.stdin)["secrets"]["db_password"]["file"]).parent)
')
    if [[ "$action" == prepare ]]; then
        exec bash "$project/scripts/setup/prepare_compose.sh" "$secret_dir"
    fi
    if [[ "$action" == start ]]; then
        bash "$project/scripts/setup/prepare_compose.sh" "$secret_dir"
        "${compose[@]}" up -d --build --wait
        exec "${compose[@]}" ps -a
    fi
    endpoint=$("${compose[@]}" port web 80)
    if [[ ! "$endpoint" =~ ^127\.0\.0\.1:([0-9]+)$ ]]; then
        echo "[FAIL] Start Compose with its web port bound to 127.0.0.1 before collecting." >&2
        exit 1
    fi
    port=${BASH_REMATCH[1]}
    collector_env="$secret_dir/collector.env"
    if [[ ! -r "$collector_env" ]]; then
        echo "[FAIL] Run compose_host.sh prepare to create the collector configuration." >&2
        exit 1
    fi
    python="$project/.venv/bin/python"
    collector_imports='import dotenv, fastapi, psutil, pydantic_settings'
    if ! "$python" -c "$collector_imports" >/dev/null 2>&1; then
        venv="$HOME/.config/serverwatch-delivery/collector-venv"
        python="$venv/bin/python"
        if ! "$python" -c "$collector_imports" >/dev/null 2>&1; then
            python3 -m venv "$venv"
            "$python" -m pip install -r "$project/backend/requirements.txt"
        fi
    fi
    unset SERVERWATCH_COLLECTOR_TOKEN SERVERWATCH_COLLECTOR_TOKEN_FILE
    exec "$python" "$project/scripts/monitoring/collect_local.py" \
        --env-file "$collector_env" --api-port "$port"
fi
exec "${compose[@]}" "$@"
