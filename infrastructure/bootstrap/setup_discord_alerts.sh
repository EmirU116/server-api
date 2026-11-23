#!/usr/bin/env bash
# Install the host-only disk alert timer. The webhook is supplied as a file.
set -Eeuo pipefail
fail() { echo "[FAIL] $*" >&2; exit 1; }

if [[ "${1:-}" == --help ]]; then
    echo 'Usage: bash infrastructure/bootstrap/setup_discord_alerts.sh WEBHOOK_FILE [THRESHOLD_PERCENT]'
    echo 'Run as the normal Ubuntu SSH user. WEBHOOK_FILE must be private (mode 600 or 400).'
    exit 0
fi
(( $# >= 1 && $# <= 2 )) || fail 'Supply a private webhook file and, optionally, a threshold.'
(( EUID != 0 )) || fail 'Run as your SSH user. Setup calls sudo when needed.'
webhook=$1
threshold=${2:-90}
[[ "$threshold" =~ ^([1-9][0-9]?|100)$ ]] || fail 'Threshold must be an integer from 1 to 100.'
[[ -f "$webhook" && ! -L "$webhook" && -O "$webhook" ]] ||
    fail 'Supply a regular webhook file owned by your SSH user.'
mode=$(stat -c '%a' -- "$webhook")
[[ "$mode" == 600 || "$mode" == 400 ]] || fail 'Run chmod 600 on the webhook file first.'
[[ -d /run/systemd/system && -x /usr/bin/python3 ]] || fail 'Ubuntu with running systemd and Python 3 is required.'
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
checker="$project/scripts/monitoring/discord_disk_alert.py"
/usr/bin/python3 "$checker" --validate-webhook "$webhook"
work_dir=$(mktemp -d)
trap 'rm -rf -- "$work_dir"' EXIT
trap 'echo "[FAIL] Discord setup stopped at line $LINENO. Review the error above." >&2' ERR
sed "s/@THRESHOLD@/$threshold/" "$project/infrastructure/systemd/serverwatch-discord.service" > "$work_dir/service"
sudo install -d -o root -g root -m 700 /etc/serverwatch-discord
sudo install -o root -g root -m 600 -- "$webhook" /etc/serverwatch-discord/webhook
sudo install -d -o root -g root -m 755 /usr/local/lib/serverwatch
sudo install -o root -g root -m 644 -- "$checker" /usr/local/lib/serverwatch/discord_disk_alert.py
sudo install -o root -g root -m 644 "$work_dir/service" /etc/systemd/system/serverwatch-discord.service
sudo install -o root -g root -m 644 "$project/infrastructure/systemd/serverwatch-discord.timer" /etc/systemd/system/serverwatch-discord.timer
sudo systemctl daemon-reload
sudo systemctl enable --now serverwatch-discord.timer
echo "[OK] Discord disk alert is scheduled with a $threshold% threshold."
echo '[INFO] Check progress with systemctl list-timers serverwatch-discord.timer.'
echo '[INFO] Inspect results with sudo journalctl -u serverwatch-discord.service -n 20.'
