#!/usr/bin/env bash
# Run as the trusted Compose operator. Keep the existing checkout, secrets and DB volume.
set -Eeuo pipefail
fail() { echo "[FAIL] $*" >&2; exit 1; }

(( $# == 5 )) || fail 'Supply environment, Git revision, API and web image digests, and the release signature.'
target=$1
revision=$2
api_image=$3
web_image=$4
signature=$5
image_ref='^ghcr[.]io/[a-z0-9._-]+/[a-z0-9._-]+-(api|web)@sha256:[0-9a-f]{64}$'
[[ "$target" == staging || "$target" == production ]] || fail 'Invalid deployment environment.'
[[ "$revision" =~ ^[0-9a-f]{40}$ ]] || fail 'Expected a full Git commit SHA.'
[[ "$api_image" =~ $image_ref && "$api_image" == *-api@sha256:* ]] || fail 'Invalid API image digest.'
[[ "$web_image" =~ $image_ref && "$web_image" == *-web@sha256:* ]] || fail 'Invalid web image digest.'
[[ "${api_image%-api@*}" == "${web_image%-web@*}" ]] || fail 'Images must belong to the same release repository.'

project="$HOME/serverwatch"
state="$HOME/.config/serverwatch-delivery"
[[ -r "$state/environment" && "$(<"$state/environment")" == "$target" ]] ||
    fail 'The host deployment environment marker does not match this job.'
[[ -r "$state/repository" && "${api_image%-api@*}" == "$(<"$state/repository")" ]] ||
    fail 'The image repository does not match the host release repository.'
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
allowed_signers="$script_dir/release-signers"
[[ -f "$allowed_signers" && -r "$allowed_signers" ]] ||
    fail 'The host release signers file is missing or unreadable.'
cd "$project" || fail 'Clone the repository to ~/serverwatch as the Compose operator first.'
umask 077
exec 9>"$state/deploy.lock"
flock -n 9 || fail 'Another deployment is already running on this host.'
trap 'echo "[FAIL] Deployment stopped at line $LINENO. Review the output, then inspect the services and database before retrying." >&2' ERR

temporary=$(mktemp "$state/.release.XXXXXX")
trap 'rm -f -- "$temporary"' EXIT
printf '%s' "$signature" | base64 --decode > "$temporary" 2>/dev/null ||
    fail 'Invalid release signature encoding.'
# The signed record is four newline-terminated fields in request order.
printf '%s\n' "$target" "$revision" "$api_image" "$web_image" |
    ssh-keygen -Y verify -f "$allowed_signers" -I "$target" -n serverwatch-release-v1 \
        -s "$temporary" >/dev/null 2>&1 ||
    fail 'Release approval signature does not match this environment, commit, and image pair.'

# Read the release config from the exact reviewed commit without editing local files.
git fetch --no-tags origin '+refs/heads/main:refs/remotes/origin/main'
git merge-base --is-ancestor "$revision" refs/remotes/origin/main ||
    fail 'The requested commit is no longer reachable from origin/main.'
manifest="$state/compose-$revision.yaml"
git show "$revision:compose.yaml" > "$temporary"
mv -- "$temporary" "$manifest"

export SERVERWATCH_API_IMAGE="$api_image" SERVERWATCH_WEB_IMAGE="$web_image"
compose=(bash "$script_dir/compose_host.sh" --file "$manifest")
# Pull the application images first. Compose creates/reuses its named DB volume.
"${compose[@]}" pull api migrate web
"${compose[@]}" up -d --no-build --wait --wait-timeout 120
address=$("${compose[@]}" port web 80)
[[ "$address" =~ ^127[.]0[.]0[.]1:[0-9]+$ ]] || fail 'The web container must publish to a loopback port.'
health=$(curl --noproxy '*' --fail --silent --show-error --max-time 10 \
    "http://$address/api/v1/health?server_id=1") || fail 'The Compose health request failed.'
python3 -c 'import json, sys; sys.exit(json.load(sys.stdin).get("status") != "healthy")' <<< "$health" ||
    fail 'The Compose API did not report healthy.'
curl --noproxy '*' --fail --silent --show-error --max-time 10 "http://$address/docs" > /dev/null ||
    fail 'The Compose Swagger request failed.'

# Advance the marker only after the release has passed the host checks.
temporary=$(mktemp "$state/.success.XXXXXX")
printf '%s\n%s\n%s\n' "$revision" "$api_image" "$web_image" > "$temporary"
if [[ -f "$state/last-success" ]] && ! cmp -s "$temporary" "$state/last-success"; then
    cp -- "$state/last-success" "$state/previous-success"
fi
mv -- "$temporary" "$state/last-success"
echo "[OK] Deployed $revision to $target and verified health and Swagger."
