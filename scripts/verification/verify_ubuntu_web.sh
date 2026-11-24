#!/usr/bin/env bash
# Reach Nginx over loopback with the public IP as the HTTP Host.
set -euo pipefail
fail() { echo "[FAIL] $*" >&2; exit 1; }
if [[ "${1:-}" == --help ]]; then
    echo "Usage: bash verify_ubuntu_web.sh PUBLIC_IPV4"
    exit 0
fi
[[ $# == 1 ]] || fail "Supply the EC2 public IPv4 address."
public_ip=$1
python3 -c 'import ipaddress, sys; ipaddress.IPv4Address(sys.argv[1])' "$public_ip" 2>/dev/null ||
    fail "Supply a valid IPv4 address."
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
bash "$project/scripts/verification/verify_ubuntu_monitoring.sh" ||
    fail "Underlying monitoring checks failed."
fetch() {
    curl --noproxy '*' --fail --silent --show-error --max-time 5 \
        --resolve "$public_ip:80:127.0.0.1" "http://$public_ip$1"
}
dashboard=$(fetch /) || fail "Dashboard request failed."
asset=$(grep -oE 'src="/assets/[^"]+\.js"' <<< "$dashboard") ||
    fail "Dashboard did not reference a built JavaScript asset."
asset=${asset#src=\"}
asset=${asset%\"}
javascript=$(fetch "$asset") || fail "Dashboard JavaScript request failed."
[[ -n "$javascript" ]] || fail "Dashboard JavaScript is empty."
docs=$(fetch /docs) || fail "Swagger request failed."
[[ "$docs" == *SwaggerUIBundle* && "$docs" == */openapi.json* ]] ||
    fail "/docs did not return Swagger UI."
schema=$(fetch /openapi.json) || fail "OpenAPI request failed."
python3 -c 'import json, sys; sys.exit("/api/v1/health" not in json.load(sys.stdin).get("paths", {}))' <<< "$schema" ||
    fail "OpenAPI did not describe the health endpoint."
health=$(fetch "/api/v1/health?server_id=1") || fail "Proxied health request failed."
python3 -c 'import json, sys; sys.exit(json.load(sys.stdin).get("status") != "healthy")' <<< "$health" ||
    fail "Proxied API did not report healthy."
echo "[PASS] Nginx served React, health, Swagger and OpenAPI."
echo "[INFO] Test from your computer to verify public access."
