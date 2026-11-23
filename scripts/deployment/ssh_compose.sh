#!/usr/bin/env bash
# Materialize SSH credentials only on the workflow runner and pin the host key.
set -Eeuo pipefail
fail() { echo "[FAIL] $*" >&2; exit 1; }
(( $# == 4 )) || fail 'Supply environment, Git SHA, API digest, and web digest.'
[[ "${DEPLOY_HOST:-}" =~ ^[A-Za-z0-9][A-Za-z0-9.-]*$ ]] || fail 'Set DEPLOY_HOST to an EC2 hostname or IPv4 address.'
[[ "${DEPLOY_USER:-}" =~ ^[a-z_][a-z0-9_-]*$ ]] || fail 'Set DEPLOY_USER to the dedicated Linux account.'
[[ -n "${DEPLOY_SSH_KEY:-}" && -n "${DEPLOY_KNOWN_HOSTS:-}" ]] ||
    fail 'Configure the environment SSH private key and independently verified known_hosts entry.'
# OpenSSH assembles remote arguments into a command. Allow only shell-safe tokens.
for argument in "$@"; do
    [[ "$argument" =~ ^[A-Za-z0-9./_@:-]+$ ]] || fail 'Invalid deployment argument.'
done

umask 077
work_dir=$(mktemp -d)
trap 'rm -rf -- "$work_dir"' EXIT
printf '%s\n' "$DEPLOY_SSH_KEY" > "$work_dir/key"
printf '%s\n' "$DEPLOY_KNOWN_HOSTS" > "$work_dir/known_hosts"
unset DEPLOY_SSH_KEY DEPLOY_KNOWN_HOSTS
ssh-keygen -F "$DEPLOY_HOST" -f "$work_dir/known_hosts" > /dev/null ||
    fail 'The pinned known_hosts entry does not match DEPLOY_HOST.'
if ! ssh -n -T -F /dev/null -i "$work_dir/key" \
    -o ClearAllForwardings=yes -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes \
    -o "UserKnownHostsFile=$work_dir/known_hosts" -o GlobalKnownHostsFile=/dev/null \
    -o ConnectTimeout=10 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
    "$DEPLOY_USER@$DEPLOY_HOST" serverwatch-deploy "$@"; then
    fail 'EC2 deployment failed. Check the SSH fingerprint, connectivity, and remote output.'
fi
