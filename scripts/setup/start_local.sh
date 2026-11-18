#!/usr/bin/env bash
# Use Windows runtimes consistently, including when this entry point runs in WSL.
set -euo pipefail

usage() {
    cat <<'HELP'
Usage: bash scripts/setup/start_local.sh [--postgres-service NAME]

Start the existing Windows PostgreSQL service, FastAPI, and React for local tests.
Run in Git Bash or WSL with Windows interop enabled. Windows Python and Node are
used for both environments. Existing .env, dependencies, and metrics migration
are required. Nothing is installed and no credentials or databases are created.
Press Ctrl+C to stop the API and frontend; PostgreSQL is left running.
HELP
}

service_name=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --postgres-service)
            if [[ $# -lt 2 || -z "$2" || "$2" == --* ]]; then
                echo "FAIL: --postgres-service requires a Windows service name." >&2
                exit 1
            fi
            service_name="$2"
            shift 2
            ;;
        *) echo "FAIL: Unknown argument: $1" >&2; usage >&2; exit 1 ;;
    esac
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
helper="$script_dir/start_local_windows.ps1"
case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) helper=$(cygpath -w "$helper") ;;
    Linux*)
        if ! command -v wslpath >/dev/null 2>&1; then
            echo "FAIL: This launcher targets the existing Windows PostgreSQL setup. Use Git Bash or WSL." >&2
            exit 1
        fi
        helper=$(wslpath -w "$helper")
        ;;
    *) echo "FAIL: Use Git Bash or WSL for this Windows launcher." >&2; exit 1 ;;
esac

if ! command -v powershell.exe >/dev/null 2>&1; then
    echo "FAIL: Windows PowerShell is unavailable. Use Git Bash or enable WSL Windows interop." >&2
    exit 1
fi

arguments=(-NoProfile -File "$helper")
if [[ -n "$service_name" ]]; then
    arguments+=(-PostgresService "$service_name")
fi
# exec preserves the exit status and lets Ctrl+C reach the Windows supervisor.
# Prevent Git Bash from rewriting arguments already converted to Windows paths.
MSYS2_ARG_CONV_EXCL='*' exec powershell.exe "${arguments[@]}"
