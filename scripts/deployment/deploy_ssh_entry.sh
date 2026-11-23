#!/usr/bin/env bash
# Read the one command supplied by sshd. Never evaluate it as shell code.
set -euo pipefail
fail() { echo '[FAIL] This SSH key only accepts a ServerWatch deployment request.' >&2; exit 1; }
(( $# == 0 )) || fail
IFS= read -r request || fail
pattern='^serverwatch-deploy ([a-z]+) ([0-9a-f]{40}) ([-a-z0-9./_@:]+) ([-a-z0-9./_@:]+) ([A-Za-z0-9+/=]+)$'
[[ "$request" =~ $pattern ]] || fail
args=("${BASH_REMATCH[@]:1}")
if IFS= read -r extra || [[ -n "$extra" ]]; then
    fail
fi
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec /usr/bin/bash "$script_dir/deploy_compose.sh" "${args[@]}"
