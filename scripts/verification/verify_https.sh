#!/usr/bin/env bash
# Check the custom domain through Nginx on this host, with real TLS validation.
set -euo pipefail
fail() { echo "[FAIL] $*" >&2; exit 1; }
if [[ "${1:-}" == --help ]]; then
    echo "Usage: bash verify_https.sh DOMAIN"
    exit 0
fi
[[ $# == 1 ]] || fail "Supply the domain."
domain=${1,,}
# A staging certificate is deliberately untrusted, so skip validation only then.
tls=()
if [[ "${SERVERWATCH_CERTBOT_STAGING:-0}" == 1 ]]; then
    tls=(--insecure)
fi
# --resolve sends the request to local Nginx while keeping the real hostname,
# so the certificate is checked exactly as a browser would check it.
request() {
    curl --noproxy '*' --silent --show-error --max-time 5 "${tls[@]}" \
        --resolve "$domain:80:127.0.0.1" --resolve "$domain:443:127.0.0.1" "$@"
}
health=$(request --fail "https://$domain/api/v1/health?server_id=1") ||
    fail "HTTPS health request failed. Check the certificate and the Nginx domain site."
python3 -c 'import json, sys; sys.exit(json.load(sys.stdin).get("status") != "healthy")' <<< "$health" ||
    fail "The API did not report healthy over HTTPS."
docs=$(request --fail "https://$domain/docs") || fail "Swagger request over HTTPS failed."
[[ "$docs" == *SwaggerUIBundle* ]] || fail "/docs did not return Swagger UI over HTTPS."
redirect=$(request --output /dev/null --write-out '%{http_code} %{redirect_url}' "http://$domain/docs") ||
    fail "HTTP request for the domain failed."
[[ "$redirect" == "301 https://$domain/docs" ]] || fail "HTTP did not redirect to HTTPS."
echo "[PASS] $domain serves health and Swagger over HTTPS and redirects HTTP."
