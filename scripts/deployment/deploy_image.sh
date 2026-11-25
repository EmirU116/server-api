#!/usr/bin/env bash
# Deploy the Docker images of one tested commit to this host's Compose stack.
# GitHub Actions runs this over SSH with a key that can run nothing else
# (see authorize_deploy_key.sh). The key's forced command fixes the image
# repository, and the commit SHA arrives as the SSH command.
#
#   by hand:     bash deploy_image.sh IMAGE_REPOSITORY COMMIT_SHA
#   from GitHub: bash deploy_image.sh IMAGE_REPOSITORY   (SHA in SSH_ORIGINAL_COMMAND)
set -euo pipefail
fail() { echo "[FAIL] $*" >&2; exit 1; }

# The git update below can rewrite this file while it runs. Bash reads a
# script as it executes it, so all the work sits in main(), which Bash reads
# completely before running it.
main() {
    if [[ "${1:-}" == --help ]]; then
        echo "Usage: bash deploy_image.sh IMAGE_REPOSITORY [COMMIT_SHA]"
        echo "Example: bash deploy_image.sh ghcr.io/owner/repo 0123...  (full 40-character SHA)"
        exit 0
    fi
    (( $# == 1 || $# == 2 )) || fail "Supply the image repository and the commit SHA."
    local repository=$1
    local sha=${2:-${SSH_ORIGINAL_COMMAND:-}}
    [[ "$repository" =~ ^ghcr\.io/[a-z0-9._-]+/[a-z0-9._-]+$ ]] ||
        fail "Supply an image repository such as ghcr.io/owner/repo, in lowercase."
    [[ "$sha" =~ ^[0-9a-f]{40}$ ]] || fail "Supply the full 40-character commit SHA."

    local project compose_host
    project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
    compose_host=$project/scripts/deployment/compose_host.sh

    echo "[DEPLOY] update the checkout to $sha"
    cd -- "$project"
    [[ "$(git symbolic-ref --quiet --short HEAD)" == main ]] ||
        fail "The checkout in $project must be on the main branch."
    git diff --quiet HEAD -- ||
        fail "The checkout has uncommitted changes. Commit or discard them, then deploy again."
    git fetch --quiet origin main
    # Only deploy what was merged to main, which is what CI tested.
    git merge-base --is-ancestor "$sha" origin/main ||
        fail "Commit $sha is not on origin/main."
    git merge --quiet --ff-only "$sha" ||
        fail "The checkout cannot fast-forward to $sha."

    # compose.yaml reads these to choose the images instead of building locally.
    export SERVERWATCH_API_IMAGE=$repository/api:$sha
    export SERVERWATCH_WEB_IMAGE=$repository/web:$sha
    echo "[DEPLOY] pull $SERVERWATCH_API_IMAGE and $SERVERWATCH_WEB_IMAGE"
    bash "$compose_host" prepare >/dev/null ||
        fail "Run bash scripts/deployment/compose_host.sh start once before automatic deploys."
    bash "$compose_host" pull api web ||
        fail "Could not pull the images. Check that both GHCR packages are public."

    echo "[DEPLOY] restart Compose; the migrate service updates the schema first"
    bash "$compose_host" up -d --no-build --wait ||
        fail "The new containers did not become healthy. Check: bash scripts/deployment/compose_host.sh logs"

    local endpoint health
    endpoint=$(bash "$compose_host" port web 80)
    health=$(curl --noproxy '*' --fail --silent --show-error --max-time 5 \
        "http://$endpoint/api/v1/health?server_id=1") ||
        fail "The health request through the Compose web container failed."
    python3 -c 'import json, sys; sys.exit(json.load(sys.stdin).get("status") != "healthy")' <<< "$health" ||
        fail "The deployed API did not report healthy."

    # Record which commit runs here, and keep its images in the host's Compose
    # settings so later manual compose_host.sh commands use them too.
    local settings=$HOME/.config/serverwatch-delivery
    printf '%s\n' "$sha" > "$settings/deployed-commit"
    grep -v '^SERVERWATCH_\(API\|WEB\)_IMAGE=' "$settings/compose.env" > "$settings/compose.env.new" || true
    printf '%s\n' "SERVERWATCH_API_IMAGE=$SERVERWATCH_API_IMAGE" \
        "SERVERWATCH_WEB_IMAGE=$SERVERWATCH_WEB_IMAGE" >> "$settings/compose.env.new"
    chmod 600 "$settings/compose.env.new"
    mv -- "$settings/compose.env.new" "$settings/compose.env"

    # Free disk space: remove the images of earlier deploys.
    local image
    while read -r image; do
        [[ "$image" == "$repository"/api:* || "$image" == "$repository"/web:* ]] || continue
        [[ "$image" != *":$sha" ]] || continue
        docker image rm "$image" >/dev/null 2>&1 || true
    done < <(docker image ls --format '{{.Repository}}:{{.Tag}}')

    echo "[PASS] Deployed $sha. The Compose API reports healthy."
}

main "$@"
