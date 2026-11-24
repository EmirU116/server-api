#!/usr/bin/env bash
# Check the native deployment on EC2.
set -euo pipefail
if [[ "${1:-}" == --help ]]; then
    echo 'Usage: bash verify.sh PUBLIC_IPV4'
    echo "Use the same optional environment as setup.sh."
    exit 0
fi
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# Run the existing checks for the native API, collector, React and Nginx.
bash "$project/scripts/verification/verify_ubuntu_web.sh" "$@"

fail() { echo "[FAIL] $*" >&2; exit 1; }

# Check that Cron is enabled and uses the backup schedule from this checkout.
systemctl is-active --quiet cron.service && systemctl is-enabled --quiet cron.service ||
    fail 'Cron must be active and enabled.'
sudo cmp -s "$project/infrastructure/cron/serverwatch-backup" /etc/cron.d/serverwatch-backup ||
    fail 'The installed backup schedule differs from the checkout.'
sudo test -x /usr/local/sbin/serverwatch-backup || fail 'The backup script is unavailable.'
# Check Docker Engine and its Compose and Buildx plugins.
systemctl is-active --quiet docker.service && docker compose version && docker buildx version ||
    fail 'Docker, Compose or Buildx is unavailable.'

# Check Discord timer scheduling and credential permissions without reading the webhook URL.
if [[ -n "${SERVERWATCH_DISCORD_WEBHOOK_FILE:-}" ]] || systemctl is-enabled --quiet serverwatch-discord.timer; then
    systemctl is-active --quiet serverwatch-discord.timer &&
        systemctl is-enabled --quiet serverwatch-discord.timer ||
        fail 'The Discord timer must be active and enabled.'
    [[ "$(sudo stat -c '%u:%g:%a' /etc/serverwatch-discord/webhook)" == 0:0:600 ]] ||
        fail 'The Discord credential must be owned by root with mode 600.'
    if [[ -n "${SERVERWATCH_DISCORD_WEBHOOK_FILE:-}" ]]; then
        threshold=${SERVERWATCH_DISCORD_THRESHOLD:-90}
        [[ "$threshold" =~ ^([1-9][0-9]?|100)$ ]] || fail 'Invalid Discord threshold.'
        systemctl show serverwatch-discord.service --property=ExecStart --value |
            grep -Eq -- "--threshold $threshold([[:space:];]|$)" ||
            fail 'The loaded Discord threshold differs from the requested setting.'
    fi
    systemctl list-timers serverwatch-discord.timer --no-pager
fi

# Check actual workspace access by running permission tests as each requested user.
if [[ -n "${SERVERWATCH_SENIOR_USER:-}" ]]; then
    login=${SERVERWATCH_SENIOR_USER,,}
    sudo -u "$login" test -w /srv/serverwatch/dev &&
        sudo -u "$login" test -w /srv/serverwatch/prod ||
        fail 'The senior developer must be able to write to dev and prod.'
fi
if [[ -n "${SERVERWATCH_JUNIOR_USER:-}" ]]; then
    login=${SERVERWATCH_JUNIOR_USER,,}
    sudo -u "$login" test -w /srv/serverwatch/dev &&
        sudo -u "$login" test -x /srv/serverwatch/prod ||
        fail 'The junior developer must have dev write access and prod traversal.'
    if sudo -u "$login" test -w /srv/serverwatch/prod; then
        fail 'The junior developer can write to prod.'
    fi
fi
# Resolve the container web port and check API health through the loopback proxy.
if [[ "${SERVERWATCH_START_COMPOSE:-0}" == 1 ]]; then
    endpoint=$(bash "$project/scripts/deployment/compose_host.sh" port web 80)
    [[ "$endpoint" =~ ^127\.0\.0\.1:[0-9]+$ ]] || fail 'Compose web is unavailable on loopback.'
    curl --noproxy '*' --fail --silent --show-error --max-time 5 \
        "http://$endpoint/api/v1/health?server_id=1" >/dev/null ||
        fail 'Compose API health check failed.'
fi
# Check that the operator aliases are present in the SSH user’s Bash configuration.
for alias_name in sw-help sw-status sw-logs sw-timers; do
    grep -Fq "alias $alias_name=" "$HOME/.bashrc" || fail "Missing Bash alias $alias_name."
done
echo '[PASS] Requested setup checks passed.'
