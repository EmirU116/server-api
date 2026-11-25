#!/usr/bin/env bash
# Serve the custom domain over HTTPS with a Let's Encrypt certificate (VG2).
# Run after setup.sh. Safe to rerun: Certbot keeps a certificate that is still
# valid, and setup.sh never overwrites the domain's Nginx site.
set -euo pipefail
fail() { echo "[FAIL] $*" >&2; exit 1; }
if [[ "${1:-}" == --help ]]; then
    echo "Usage: bash setup_https.sh DOMAIN PUBLIC_IPV4"
    echo "Optional environment: SERVERWATCH_CERTBOT_EMAIL (expiry notices),"
    echo "SERVERWATCH_CERTBOT_STAGING=1 (untrusted test certificate for rehearsals)."
    exit 0
fi
preflight=false
if [[ "${1:-}" == --preflight ]]; then
    preflight=true
    shift
fi
(( $# == 2 )) || fail "Supply the domain and the EC2 public IPv4 address."
domain=${1,,}
public_ip=$2
[[ "$domain" =~ ^([a-z0-9]([a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}$ ]] ||
    fail "Supply a domain such as example.com, without a scheme, port, or path."
[[ "$domain" != www.* ]] || fail "Supply the domain without www. It is added when its DNS record exists."
python3 -c 'import ipaddress, sys; ipaddress.IPv4Address(sys.argv[1])' "$public_ip" 2>/dev/null ||
    fail "Supply an IPv4 address without a scheme or port."
(( EUID != 0 )) || fail "Run as the setup user, without sudo before bash."

# Let's Encrypt connects to the domain, so DNS must already point at this server.
points_here() { getent ahostsv4 "$1" | awk '{print $1}' | grep -Fqx -- "$public_ip"; }
points_here "$domain" ||
    fail "DNS for $domain does not point to $public_ip yet. Add an A record and wait a few minutes."
server_names=$domain
if points_here "www.$domain"; then
    server_names+=" www.$domain"
fi
if [[ "$preflight" == true ]]; then exit 0; fi

project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
[[ -f /etc/nginx/sites-enabled/serverwatch.conf ]] ||
    fail "Run setup.sh first so Nginx serves ServerWatch."
site=/etc/nginx/sites-enabled/serverwatch-domain.conf
certificate=/etc/letsencrypt/live/$domain/fullchain.pem
work_dir=$(mktemp -d)
trap 'rm -rf -- "$work_dir"' EXIT

# Install a rendered site, keeping the previous one if Nginx rejects it.
install_site() {
    sed -e "s/@SERVER_NAMES@/$server_names/g" -e "s/@DOMAIN@/$domain/g" "$@" > "$work_dir/site"
    if sudo test -e "$site"; then
        sudo cp -- "$site" "$work_dir/previous-site"
    fi
    sudo install -m 644 "$work_dir/site" "$site"
    if ! sudo nginx -t; then
        if [[ -f "$work_dir/previous-site" ]]; then
            sudo install -m 644 "$work_dir/previous-site" "$site"
        else
            sudo rm -- "$site"
        fi
        fail "Nginx rejected the domain site. Previous configuration restored."
    fi
    sudo systemctl reload nginx
}

echo "[SETUP] install Certbot"
if ! command -v certbot >/dev/null; then
    sudo apt-get update
    sudo apt-get install -y certbot
fi

nginx_dir=$project/infrastructure/nginx
sudo install -d -m 755 /var/www/letsencrypt
# Without a certificate, Nginx cannot load the HTTPS block yet, so start by
# answering only the ownership check over HTTP.
if ! sudo test -e "$certificate"; then
    echo "[SETUP] answer the Let's Encrypt check for $server_names"
    install_site "$nginx_dir/serverwatch-domain-http.conf"
fi

echo "[SETUP] request the certificate"
certbot_args=(certonly --webroot -w /var/www/letsencrypt --cert-name "$domain"
    --non-interactive --agree-tos --keep-until-expiring --expand
    --deploy-hook 'systemctl reload nginx')
for name in $server_names; do
    certbot_args+=(-d "$name")
done
if [[ -n "${SERVERWATCH_CERTBOT_EMAIL:-}" ]]; then
    certbot_args+=(--email "$SERVERWATCH_CERTBOT_EMAIL")
else
    certbot_args+=(--register-unsafely-without-email)
fi
if [[ "${SERVERWATCH_CERTBOT_STAGING:-0}" == 1 ]]; then
    certbot_args+=(--staging)
fi
sudo certbot "${certbot_args[@]}" || fail "Certbot could not issue the certificate. Check DNS and that port 80 is open."

echo "[SETUP] serve $domain over HTTPS"
install_site "$nginx_dir/serverwatch-domain-http.conf" "$nginx_dir/serverwatch-domain-https.conf"

echo "[SETUP] check automatic renewal"
systemctl is-active --quiet certbot.timer || fail "The certbot.timer renewal schedule is not active."
sudo certbot renew --dry-run --cert-name "$domain" || fail "The renewal test failed."

bash "$project/scripts/verification/verify_https.sh" "$domain"
echo "[OK] Open https://$domain/ and https://$domain/docs after allowing HTTPS (443) in EC2."
