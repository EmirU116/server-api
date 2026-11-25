#!/usr/bin/env bash
# Let GitHub Actions deploy to this host with its own SSH key (VG4).
# The key is restricted: it cannot open a shell, forward ports or run any
# command except deploy_image.sh. Run as the user who runs Compose.
set -euo pipefail
fail() { echo "[FAIL] $*" >&2; exit 1; }
if [[ "${1:-}" == --help ]]; then
    echo "Usage: bash authorize_deploy_key.sh PUBLIC_KEY_FILE SSH_HOST"
    echo "SSH_HOST is the address GitHub connects to: the Elastic IP or the domain."
    exit 0
fi
(( $# == 2 )) || fail "Supply the GitHub deploy key's public key file and the SSH host."
key_file=$1
ssh_host=$2
(( EUID != 0 )) || fail "Run as the Compose user, without sudo."
[[ "$ssh_host" =~ ^[A-Za-z0-9.-]+$ ]] || fail "Supply the host without a user, scheme or port."

# Exactly one ed25519 public key, without options of its own.
[[ -r "$key_file" ]] || fail "Cannot read $key_file."
(( $(grep -c . "$key_file") == 1 )) || fail "$key_file must contain exactly one public key."
read -r key_type key_blob key_comment < "$key_file" || true
[[ "$key_type" == ssh-ed25519 && "$key_blob" =~ ^[A-Za-z0-9+/=]+$ ]] ||
    fail "$key_file must be an ssh-ed25519 public key (ssh-keygen -t ed25519)."

project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
# Images are published as ghcr.io/<owner>/<repo>, always in lowercase.
origin=$(git -C "$project" remote get-url origin)
[[ "$origin" =~ github\.com[:/]([^/]+)/([^/]+)$ ]] ||
    fail "The checkout's origin is not a GitHub repository."
repo_name=${BASH_REMATCH[2]%.git}
repository=ghcr.io/${BASH_REMATCH[1],,}/${repo_name,,}

groups=" $(id -nG) "
[[ "$groups" == *" docker "* ]] ||
    fail "$(id -un) is not in the docker group, so deploys could not run Compose."

command="bash $project/scripts/deployment/deploy_image.sh $repository"
line="restrict,command=\"$command\" ssh-ed25519 $key_blob ${key_comment:-github-deploy}"
authorized=$HOME/.ssh/authorized_keys
install -d -m 700 "$HOME/.ssh"
touch "$authorized"
chmod 600 "$authorized"
# Replace an earlier entry for the same key instead of adding a duplicate.
grep -vF -- " $key_blob" "$authorized" > "$authorized.new" || true
printf '%s\n' "$line" >> "$authorized.new"
mv -- "$authorized.new" "$authorized"
chmod 600 "$authorized"
echo "[OK] The key can only run: $command"

host_key_file=${SERVERWATCH_SSH_HOST_KEY_FILE:-/etc/ssh/ssh_host_ed25519_key.pub}
read -r host_type host_blob _ < "$host_key_file" || fail "Cannot read $host_key_file."
echo
echo "Add these repository secrets in GitHub (Settings > Secrets and variables > Actions):"
echo "  SERVERWATCH_DEPLOY_HOST         $ssh_host"
echo "  SERVERWATCH_DEPLOY_USER         $(id -un)"
echo "  SERVERWATCH_DEPLOY_SSH_KEY      the PRIVATE key that matches $key_file"
echo "  SERVERWATCH_DEPLOY_KNOWN_HOSTS  $ssh_host $host_type $host_blob"
