#!/usr/bin/env bash
# Share host settings between manual Compose commands and approved releases.
set -euo pipefail
project="$HOME/serverwatch"
config="$HOME/.config/serverwatch-delivery/compose.env"
if [[ ! -f "$config" || ! -r "$config" ]]; then
    echo "[FAIL] Create the Compose operator's configuration at $config." >&2
    exit 1
fi

# Shell exports would otherwise override the explicit host env file.
unset SERVERWATCH_WEB_PORT SERVERWATCH_COMPOSE_SECRETS
export SERVERWATCH_WEB_BIND=127.0.0.1
export SERVERWATCH_RUNTIME_UID="$(id -u)" SERVERWATCH_RUNTIME_GID="$(id -g)"
compose=(docker compose --project-directory "$project" --project-name serverwatch --env-file "$config")
if [[ "${1:-}" != --file ]]; then
    compose+=(--file "$project/compose.yaml")
fi
if [[ "${1:-}" == prepare && $# == 1 ]]; then
    secret_dir=$("${compose[@]}" config --format json | python3 -c '
import json
from pathlib import Path
import sys

print(Path(json.load(sys.stdin)["secrets"]["db_password"]["file"]).parent)
')
    exec bash "$project/scripts/setup/prepare_compose.sh" "$secret_dir"
fi
exec "${compose[@]}" "$@"
