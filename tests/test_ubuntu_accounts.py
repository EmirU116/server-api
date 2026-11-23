"""Check account provisioning with simulated administrator commands."""

import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/setup/provision_ubuntu_user.sh"


def run_provisioner(tmp_path, *args, memberships="", unsafe_workspace=False):
    workspace = tmp_path / "workspace"
    if unsafe_workspace:
        workspace.symlink_to(tmp_path, target_is_directory=True)
    shell = """
        source "$1"
        workspace=$2
        mock_memberships=$3
        shift 3
        require_platform() { :; }
        getent() { [[ -n "$mock_memberships" ]]; }
        id() { echo "$mock_memberships"; }
        stat() { echo "0 755"; }
        groupadd() { printf 'groupadd %s\n' "$*"; }
        useradd() { printf 'useradd %s\n' "$*"; }
        install() { mkdir -- "${@: -1}"; }
        chgrp() { :; }
        chmod() { :; }
        setfacl() { printf 'setfacl %s\n' "$*"; }
        main "$@"
    """
    return subprocess.run(
        ["bash", "-c", shell, "_", str(SCRIPT), str(workspace), memberships, *args],
        check=False,
        text=True,
        capture_output=True,
        timeout=10,
    )


@pytest.mark.parametrize(
    ("name", "role", "group"),
    [
        ("ServerWatchTestJunior", "junior developer", "serverwatch-junior"),
        ("ServerWatchTestSenior", "senior developer", "serverwatch-senior"),
    ],
)
def test_new_user_and_workspace_access(tmp_path, name, role, group):
    result = run_provisioner(tmp_path, name, role)

    assert result.returncode == 0, result.stderr
    assert (
        f"--groups {group} --key HOME_MODE=0700 --password ! {name.lower()}"
        in result.stdout
    )
    assert "groupadd --force serverwatch-senior" in result.stdout
    assert "groupadd --force serverwatch-junior" in result.stdout
    acl_commands = [
        line for line in result.stdout.splitlines() if line.startswith("setfacl ")
    ]
    assert len(acl_commands) == 2
    assert acl_commands[0].count("g:serverwatch-junior:rwx") == 2
    assert acl_commands[0].endswith("/dev")
    assert acl_commands[1].count("g:serverwatch-junior:r-x") == 2
    assert acl_commands[1].endswith("/prod")


@pytest.mark.parametrize(
    ("memberships", "expected", "error"),
    [
        ("alice serverwatch-junior", 0, ""),
        ("alice sudo", 1, "different role or is unmanaged"),
        ("alice serverwatch-senior", 1, "different role or is unmanaged"),
        ("alice serverwatch-junior serverwatch-senior", 1, "both roles"),
    ],
)
def test_existing_accounts_are_reused_only_for_same_role(
    tmp_path, memberships, expected, error
):
    result = run_provisioner(
        tmp_path, "Alice", "junior developer", memberships=memberships
    )

    assert result.returncode == expected
    assert error in result.stderr
    assert "useradd" not in result.stdout
    if expected:
        assert "groupadd" not in result.stdout


@pytest.mark.parametrize(
    "arguments",
    [
        (),
        ("../Alice", "junior developer"),
        ("Alice\n", "junior developer"),
        ("Alice", "admin"),
    ],
)
def test_invalid_inputs_are_rejected_before_provisioning(tmp_path, arguments):
    result = run_provisioner(tmp_path, *arguments)

    assert result.returncode == 1
    assert "[FAIL]" in result.stderr
    assert result.stdout == ""


def test_refuses_workspace_symlink(tmp_path):
    result = run_provisioner(
        tmp_path, "Alice", "junior developer", unsafe_workspace=True
    )

    assert result.returncode == 1
    assert "must be a real directory" in result.stderr
    assert "setfacl" not in result.stdout
    assert "useradd" not in result.stdout
