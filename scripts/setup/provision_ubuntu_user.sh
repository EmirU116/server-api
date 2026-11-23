#!/usr/bin/env bash
# Provision a password-locked Linux account and access to managed workspaces.
set -euo pipefail

fail() { echo "[FAIL] $*" >&2; exit 1; }

senior_group=serverwatch-senior
junior_group=serverwatch-junior
workspace=/srv/serverwatch

usage() {
    cat <<'USAGE'
Usage: sudo bash scripts/setup/provision_ubuntu_user.sh NAME ROLE
Roles: "junior developer" or "senior developer"
Example: sudo bash scripts/setup/provision_ubuntu_user.sh Alice "junior developer"
The Linux login is lowercase. Configure its SSH public key separately.
USAGE
}

require_platform() {
    (( EUID == 0 )) || fail "Run with sudo as the EC2 administrator."
    source /etc/os-release
    [[ "${ID:-}" == ubuntu ]] || fail "Run this on Ubuntu."
    command -v setfacl >/dev/null ||
        fail "Install the acl package first: sudo apt-get install -y acl"
}

check_managed_directory() {
    local path=$1 owner mode
    [[ -d "$path" && ! -L "$path" ]] || fail "$path must be a real directory."
    read -r owner mode < <(stat -c '%u %a' -- "$path")
    [[ "$owner" == 0 ]] || fail "$path must be owned by root."
    if [[ "$path" != "$workspace/dev" && "$path" != "$workspace/prod" ]]; then
        (( (8#$mode & 022) == 0 )) || fail "$path must only be writable by root."
    fi
}

prepare_workspace() {
    local directory junior_permissions
    check_managed_directory /srv
    if [[ ! -e "$workspace" && ! -L "$workspace" ]]; then
        install -d -o root -g root -m 0755 "$workspace"
    fi
    check_managed_directory "$workspace"

    for directory in dev prod; do
        local path="$workspace/$directory"
        if [[ ! -e "$path" && ! -L "$path" ]]; then
            install -d -o root -g "$senior_group" -m 2770 "$path"
        fi
        check_managed_directory "$path"
        chgrp -- "$senior_group" "$path"
        junior_permissions=rwx
        if [[ "$directory" == prod ]]; then junior_permissions=r-x; fi
        # The setgid group owns new entries. Default ACLs also carry the junior
        # role's permissions into newly created files and directories.
        local entries="u::rwx,g::rwx,g:$junior_group:$junior_permissions,m::rwx,o::---"
        local defaults="d:u::rwx,d:g::rwx,d:g:$junior_group:$junior_permissions,d:m::rwx,d:o::---"
        setfacl --set "$entries,$defaults" -- "$path"
        chmod g+s -- "$path"
    done
}

main() {
    if [[ $# == 1 && "$1" == --help ]]; then usage; return; fi
    (( $# == 2 )) || fail 'Supply NAME and a quoted role. Run with --help for examples.'

    local user role memberships create_user=false LC_ALL=C
    [[ "$1" =~ ^[a-zA-Z][a-zA-Z0-9_-]{0,30}$ ]] ||
        fail "Use a Linux login starting with a letter, at most 31 characters."
    user=$(tr '[:upper:]' '[:lower:]' <<< "$1")
    case "$2" in
        "junior developer") role=$junior_group ;;
        "senior developer") role=$senior_group ;;
        *) fail 'Choose "junior developer" or "senior developer".' ;;
    esac

    require_platform
    trap 'echo "[FAIL] Provisioning stopped at line $LINENO. Review the error above." >&2' ERR
    if getent passwd "$user" >/dev/null; then
        # Reuse only an account already assigned to this role. This avoids
        # changing baseline users such as ubuntu or silently promoting accounts.
        memberships=" $(id -nG "$user") "
        [[ "$memberships" == *" $role "* ]] ||
            fail "Existing account $user has a different role or is unmanaged. Choose another name."
        if [[ "$memberships" == *" $senior_group "* && "$memberships" == *" $junior_group "* ]]; then
            fail "Existing account $user has both roles. Review its group memberships."
        fi
    else
        [[ ! -e "/home/$user" && ! -L "/home/$user" ]] ||
            fail "The home directory for $user already exists. Choose another account name."
        create_user=true
    fi

    groupadd --force "$senior_group"
    groupadd --force "$junior_group"
    prepare_workspace
    if [[ "$create_user" == true ]]; then
        useradd --create-home --home-dir "/home/$user" --user-group --shell /bin/bash --groups "$role" \
            --key HOME_MODE=0700 --password '!' "$user"
    fi
    printf '[OK] %s belongs to %s. Workspaces are under %s.\n' "$user" "$role" "$workspace"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
