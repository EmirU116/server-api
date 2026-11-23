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

python3 - "$secret_dir" <<'PY'
import json
import os
import platform
import secrets
import stat
import sys
from pathlib import Path

directory = Path(sys.argv[1]).expanduser()


def require_private(path, kind, mode):
    info = path.lstat()
    if not kind(info.st_mode) or info.st_uid != os.getuid():
        raise SystemExit(f"[FAIL] {path.name} must be owned by this user and must not be a symlink.")
    if stat.S_IMODE(info.st_mode) != mode:
        raise SystemExit(f"[FAIL] {path.name} requires permissions {mode:o}.")


def preserve_or_create(name, content):
    path = directory / name
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(content + "\n")
    except FileExistsError:
        pass
    require_private(path, stat.S_ISREG, 0o600)


try:
    directory.mkdir(parents=True, exist_ok=True)
    require_private(directory, stat.S_ISDIR, 0o700)
    for name in ("db_admin_password", "db_password", "reader_token", "collector_token", "admin_token"):
        preserve_or_create(name, secrets.token_urlsafe(32))

    os_type = platform.system()
    release = platform.freedesktop_os_release() if os_type == "Linux" else {}
    identity = {
        "hostname": platform.node(),
        "os_type": os_type,
        "os_name": release.get("NAME", os_type),
        "os_version": release.get("VERSION_ID", platform.release()),
        "architecture": platform.machine(),
    }
    preserve_or_create("host_identity.json", json.dumps(identity))
    token_path = str((directory / "collector_token").absolute())
    path_value = token_path.replace("\\", "\\\\").replace("'", "\\'")
    # Compose keeps the host collector's credentials independent from native services.
    preserve_or_create("collector.env", f"SERVERWATCH_COLLECTOR_TOKEN_FILE='{path_value}'")
except OSError:
    raise SystemExit("[FAIL] Could not provision private Compose files. Check ownership and write permissions.") from None

print("[OK] Compose files are ready. Existing credentials were preserved.")
PY
