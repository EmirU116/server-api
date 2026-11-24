#!/usr/bin/env bash
# Publish React and Swagger through Nginx. Called by the root setup.sh, first
# with --preflight to validate arguments before anything is installed.
set -euo pipefail
fail() { echo "[FAIL] $*" >&2; exit 1; }
if [[ "${1:-}" == --help ]]; then
    echo "Usage: bash setup_ubuntu_web.sh PUBLIC_IPV4 [PUBLIC_DNS_NAME]"
    exit 0
fi
preflight=false
if [[ "${1:-}" == --preflight ]]; then
    preflight=true
    shift
fi
(( $# >= 1 && $# <= 2 )) || fail "Supply the EC2 public IPv4 address and optionally its public DNS name."
public_ip=$1
public_dns=${2:-}
if [[ -n "$public_dns" && ! "$public_dns" =~ ^[a-zA-Z0-9]+([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]+([a-zA-Z0-9-]*[a-zA-Z0-9])?)+$ ]]; then
    fail "Supply a DNS name without a scheme, port, or path."
fi
(( EUID != 0 )) || fail "Run as the monitoring installer user, without sudo before bash."
source /etc/os-release
[[ "$ID" == ubuntu && -d /run/systemd/system ]] || fail "Ubuntu with systemd is required."
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
python3 -c 'import ipaddress, sys; ipaddress.IPv4Address(sys.argv[1])' "$public_ip" 2>/dev/null ||
    fail "Supply an IPv4 address without a scheme or port."
node_ready() {
    command -v node >/dev/null && command -v npm >/dev/null &&
        node -e 'const [major, minor] = process.versions.node.split(".").map(Number); process.exit(major > 22 || (major === 22 && minor >= 12) ? 0 : 1)'
}

install_node() (
    case "$(uname -m)" in
        x86_64) arch=x64 ;;
        aarch64) arch=arm64 ;;
        *) fail "Install Node.js 22.12+ with npm for this CPU architecture first." ;;
    esac
    release="https://nodejs.org/dist/$node_version"
    archive="node-$node_version-linux-$arch.tar.xz"
    mkdir -p -- "$(dirname -- "$node_dir")" || exit 1
    staging=$(mktemp -d -- "$(dirname -- "$node_dir")/download.XXXXXXXX") || exit 1
    trap 'rm -rf -- "$staging"' EXIT
    cd "$staging" || exit 1
    echo "[SETUP] Installing Node.js $node_version and npm for the frontend build."
    curl -fsSL --retry 3 -O "$release/SHASUMS256.txt" || exit 1
    curl -fsSL --retry 3 -O "$release/$archive" || exit 1
    awk -v archive="$archive" '$2 == archive' SHASUMS256.txt | sha256sum -c - || exit 1
    tar -xJf "$archive" || exit 1
    mv -T -- "${archive%.tar.xz}" "$node_dir"
)

if [[ "$preflight" == true ]]; then exit 0; fi
if ! node_ready; then
    node_version=v22.23.5
    node_dir="$HOME/.local/share/serverwatch/node-$node_version"
    if [[ ! -d "$node_dir" ]]; then
        install_node || fail "Could not install Node.js from nodejs.org."
    fi
    export PATH="$node_dir/bin:$PATH"
    node_ready || fail "The ServerWatch Node.js installation is unusable: $node_dir"
fi
[[ "$(systemctl show serverwatch-api -p User --value)" == "$(id -un)" &&
   "$(systemctl show serverwatch-api -p WorkingDirectory --value)" == "$project" ]] ||
    fail "Run from the checkout used by the API service, as its owner."
for service in postgresql serverwatch-api serverwatch-collector; do
    systemctl is-active --quiet "$service" || fail "$service is inactive. Set up monitoring first."
done

step="build the React frontend"
trap 'echo "[FAIL] Could not $step. Review the output above." >&2' ERR
echo "[SETUP] $step"
cd "$project/frontend"
npm ci --include=optional --include=dev
npm run build
[[ -s dist/index.html ]] || fail "Missing dist/index.html after building React."

step="install and configure Nginx"
echo "[SETUP] $step"
work_dir=$(mktemp -d)
trap 'rm -rf -- "$work_dir"' EXIT
site=/etc/nginx/sites-enabled/serverwatch.conf
server_names=$public_ip
if [[ -n "$public_dns" ]]; then
    # Nginx keeps regex names out of its hash table. Escape DNS label separators
    # and anchor the match so only the supplied hostname is accepted.
    dns_pattern=${public_dns//./[.]}
    server_names+=" ~(?i)^${dns_pattern}\$"
fi
sed "s/@SERVER_NAMES@/$server_names/g" "$project/infrastructure/nginx/serverwatch.conf" > "$work_dir/site"
sudo nginx -t
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
    fail "Nginx rejected the site. Previous configuration restored."
fi
sudo install -d -m 755 /var/www/serverwatch
sudo cp -R -- dist/. /var/www/serverwatch/
sudo chmod -R a+rX /var/www/serverwatch

step="enable Swagger on the existing API service"
echo "[SETUP] $step"
# This drop-in leaves the monitoring unit and its private environment file intact.
dropin=/etc/systemd/system/serverwatch-api.service.d
printf '[Service]\nEnvironment=SERVERWATCH_EXPOSE_API_DOCS=true\n' > "$work_dir/docs.conf"
sudo install -d -m 755 "$dropin"
sudo install -m 644 "$work_dir/docs.conf" "$dropin/60-serverwatch-web.conf"
sudo systemctl daemon-reload
sudo systemctl restart serverwatch-api
sudo systemctl enable --now nginx
sudo systemctl reload nginx

step="verify the website"
bash "$project/scripts/verification/verify_ubuntu_web.sh" "$public_ip"
echo "[OK] Open http://$public_ip/ and http://$public_ip/docs after allowing HTTP in EC2."
