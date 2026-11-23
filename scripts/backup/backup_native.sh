#!/usr/bin/env bash
# Create a private snapshot of the native Ubuntu database and service logs.
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
umask 077

if [[ "${1:-}" == --help && $# == 1 ]]; then
    echo 'Usage: sudo /usr/local/sbin/serverwatch-backup'
    echo 'Writes a PostgreSQL dump and service logs to /var/backups/serverwatch.'
    exit 0
fi
if (( $# != 0 || EUID != 0 )); then
    echo '[FAIL] Run the installed backup script as root with no arguments.' >&2
    exit 1
fi

backup_dir=/var/backups/serverwatch
install -d -o root -g root -m 700 -- "$backup_dir"
exec 9>"$backup_dir/.lock"
flock -n 9 || { echo '[FAIL] A ServerWatch backup is already running.' >&2; exit 1; }
staging=$(mktemp -d -- "$backup_dir/.pending.XXXXXXXX")
trap 'rm -rf -- "$staging"' EXIT

runuser -u postgres -- env -i PATH="$PATH" pg_dump --no-password \
    --host=/var/run/postgresql --port=5432 --username=postgres \
    --format=custom --dbname=serverwatch_monitor > "$staging/database.dump"
pg_restore --list "$staging/database.dump" > /dev/null
journalctl --no-pager --since '24 hours ago' \
    -u serverwatch-api.service -u serverwatch-collector.service \
    -u serverwatch-discord.service > "$staging/services.log"

snapshot="$backup_dir/$(date -u +%Y%m%dT%H%M%S.%NZ)"
mv -T -- "$staging" "$snapshot"
echo "[OK] ServerWatch backup saved to $snapshot"
