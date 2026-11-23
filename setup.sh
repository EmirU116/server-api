#!/usr/bin/env bash
# Install native Ubuntu monitoring and publish the dashboard.
set -euo pipefail

if [[ "${1:-}" == --help ]]; then
    echo 'Usage: bash setup.sh PUBLIC_IPV4 [PUBLIC_DNS_NAME]'
    exit 0
fi
project=${SERVERWATCH_PROJECT_DIR:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)}
bash "$project/infrastructure/bootstrap/setup_ubuntu_web.sh" --preflight "$@"
SERVERWATCH_FULL_SETUP=1 bash "$project/infrastructure/bootstrap/setup_ubuntu_monitoring.sh" "$project"
SERVERWATCH_FULL_SETUP=1 bash "$project/infrastructure/bootstrap/setup_ubuntu_web.sh" "$@"
