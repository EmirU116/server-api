#!/usr/bin/env bash
# Check the native deployment on EC2.
set -euo pipefail
if [[ "${1:-}" == --help ]]; then
    echo 'Usage: bash verify.sh PUBLIC_IPV4'
    exit 0
fi
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec bash "$project/scripts/verification/verify_ubuntu_web.sh" "$@"
