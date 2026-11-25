#!/usr/bin/env bash
# Install native Ubuntu monitoring and publish the dashboard.
set -euo pipefail

if [[ "${1:-}" == --help ]]; then
    echo 'Usage: bash setup.sh PUBLIC_IPV4 [PUBLIC_DNS_NAME]'
    echo 'Optional environment: SERVERWATCH_DISCORD_WEBHOOK_FILE, SERVERWATCH_DISCORD_THRESHOLD,'
    echo 'SERVERWATCH_SENIOR_USER, SERVERWATCH_JUNIOR_USER, SERVERWATCH_START_COMPOSE=1,'
    echo 'SERVERWATCH_DOMAIN (HTTPS with Certbot), SERVERWATCH_CERTBOT_EMAIL, SERVERWATCH_CERTBOT_STAGING=1.'
    exit 0
fi
# Use the cloned checkout when this entry point was copied to EC2 with SCP.
project=${SERVERWATCH_PROJECT_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)}
# Accept the path to a private credential file for the optional Discord setup.
webhook=${SERVERWATCH_DISCORD_WEBHOOK_FILE:-}
if [[ -n "$webhook" && ! -r "$webhook" ]]; then
    echo '[FAIL] The Discord webhook file must be readable.' >&2
    exit 1
fi
if [[ "${SERVERWATCH_START_COMPOSE:-0}" == 1 && "$project" != "$HOME/serverwatch" ]]; then
    echo '[FAIL] Compose expects the checkout at ~/serverwatch.' >&2
    exit 1
fi
# Validate the host and public address before installing packages or restarting services.
bash "$project/infrastructure/bootstrap/setup_ubuntu_web.sh" --preflight "$@"
# Check the domain and its DNS record now, so a typo fails before anything changes.
if [[ -n "${SERVERWATCH_DOMAIN:-}" ]]; then
    bash "$project/infrastructure/bootstrap/setup_https.sh" --preflight "$SERVERWATCH_DOMAIN" "$1"
fi
# Install packages, PostgreSQL, the API and collector services, and the Cron backup schedule.
bash "$project/infrastructure/bootstrap/setup_ubuntu_monitoring.sh" "$project"
# Build and publish React, then configure Nginx to serve it and proxy the API.
bash "$project/infrastructure/bootstrap/setup_ubuntu_web.sh" "$@"

# Provision optional Linux accounts with group and ACL access to the dev and prod workspaces.
if [[ -n "${SERVERWATCH_SENIOR_USER:-}" ]]; then
    sudo bash "$project/scripts/setup/provision_ubuntu_user.sh" "$SERVERWATCH_SENIOR_USER" "senior developer"
fi
if [[ -n "${SERVERWATCH_JUNIOR_USER:-}" ]]; then
    sudo bash "$project/scripts/setup/provision_ubuntu_user.sh" "$SERVERWATCH_JUNIOR_USER" "junior developer"
fi
# Install the systemd disk-check timer with the configured threshold.
if [[ -n "$webhook" ]]; then
    bash "$project/infrastructure/bootstrap/setup_discord_alerts.sh" "$webhook" "${SERVERWATCH_DISCORD_THRESHOLD:-90}"
fi
# Start the optional container stack alongside the native deployment.
if [[ "${SERVERWATCH_START_COMPOSE:-0}" == 1 ]]; then
    bash "$project/scripts/deployment/compose_host.sh" start
fi
# Serve the custom domain over HTTPS with a Certbot certificate.
if [[ -n "${SERVERWATCH_DOMAIN:-}" ]]; then
    bash "$project/infrastructure/bootstrap/setup_https.sh" "$SERVERWATCH_DOMAIN" "$1"
fi
# Add operator shortcuts once. New interactive Bash sessions load them from .bashrc.
if ! grep -Fqx '# ServerWatch operator aliases' "$HOME/.bashrc" 2>/dev/null; then
    cat >> "$HOME/.bashrc" <<'ALIASES'

# ServerWatch operator aliases
alias sw-status='systemctl status serverwatch-api.service serverwatch-collector.service --no-pager'
alias sw-logs='sudo journalctl -u serverwatch-api.service -n 30 --no-pager'
alias sw-timers='systemctl list-timers serverwatch-discord.timer --no-pager'
ALIASES
fi
# Install help separately so existing deployments get it on the next setup run.
if ! grep -q '^alias sw-help=' "$HOME/.bashrc"; then
    cat >> "$HOME/.bashrc" <<'ALIASES'
alias sw-help='printf "%s\n" "ServerWatch commands" "  sw-help    Show this list" "  sw-status  Show API and collector service status" "  sw-logs    Show recent API logs" "  sw-timers  Show the Discord alert schedule" "  bash setup.sh --help   Show setup options" "  bash verify.sh --help  Show verification usage"'
ALIASES
fi
echo '[INFO] Open a new Bash session and run sw-help for ServerWatch commands.'
echo '[INFO] Run bash verify.sh with the same optional environment.'
