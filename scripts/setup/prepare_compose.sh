#!/usr/bin/env bash
# Generate Compose credentials and the native host identity without printing either.
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
    echo "Usage: bash scripts/setup/prepare_compose.sh [private-secret-directory]"
    exit 0
fi
if (( $# > 1 )) || [[ "${1:-}" == -* ]]; then
    echo "[FAIL] Supply at most one private secret directory. See --help." >&2
    exit 1
fi

project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
secret_dir=${1:-${SERVERWATCH_COMPOSE_SECRETS:-$project/secrets}}
umask 077

python3 - "$secret_dir" "$project" <<'PY'
import json
import secrets
import sys
from pathlib import Path

directory = Path(sys.argv[1]).expanduser()
project = Path(sys.argv[2])
# Reuse the API's host identity rules and the native setup's private-file checks.
sys.path[:0] = [str(project / "scripts/setup"), str(project / "backend")]
from app.host_identity import ServerInfoUnavailable, read_host_info  # noqa: E402
from private_files import NotPrivate, private_directory, private_file  # noqa: E402

try:
    private_directory(directory)
    for name in (
        "db_admin_password", "db_password", "db_migration_password",
        "reader_token", "collector_token", "admin_token",
    ):
        private_file(directory / name, secrets.token_urlsafe(32) + "\n")

    # The API container cannot see the host, so record the host identity here.
    private_file(directory / "host_identity.json", json.dumps(read_host_info()) + "\n")
    token_path = str((directory / "collector_token").absolute())
    path_value = token_path.replace("\\", "\\\\").replace("'", "\\'")
    # Compose keeps the host collector's credentials independent from native services.
    private_file(directory / "collector.env", f"SERVERWATCH_COLLECTOR_TOKEN_FILE='{path_value}'\n")
except NotPrivate as error:
    raise SystemExit(f"[FAIL] {error}") from None
except ServerInfoUnavailable:
    raise SystemExit("[FAIL] Run this on the host, not inside a container.") from None
except OSError:
    raise SystemExit("[FAIL] Could not provision private Compose files. Check ownership and write permissions.") from None

print("[OK] Compose files are ready. Existing credentials were preserved.")
PY
