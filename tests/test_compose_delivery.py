"""Exercise release, trust and failure checks without registry access or SSH."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "scripts/deployment/deploy_compose.sh"
SSH = ROOT / "scripts/deployment/ssh_compose.sh"
REVISION = "1" * 40
API_IMAGE = "ghcr.io/example/serverwatch-api@sha256:" + "a" * 64
WEB_IMAGE = "ghcr.io/example/serverwatch-web@sha256:" + "b" * 64


def command(path, name, body):
    wrapper = path / name
    wrapper.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + body)
    wrapper.chmod(0o755)


@pytest.fixture
def host(tmp_path):
    directory = tmp_path / "bin"
    directory.mkdir()
    (tmp_path / "serverwatch").mkdir()
    state = tmp_path / ".config/serverwatch-delivery"
    state.mkdir(parents=True)
    (state / "environment").write_text("staging\n")
    (state / "last-success").write_text("previous\n")
    command(
        directory,
        "git",
        'printf "git %s\n" "$*" >> "$CALLS"\n'
        'if [[ "$1" == show ]]; then echo reviewed-compose; fi\n'
        'if [[ "$1" == merge-base && "${STALE:-0}" == 1 ]]; then exit 1; fi\n',
    )
    command(
        directory,
        "docker",
        '[[ "$SERVERWATCH_WEB_BIND" == 127.0.0.1 ]]\n'
        '[[ "$SERVERWATCH_RUNTIME_UID" == "$(id -u)" ]]\n'
        '[[ "$SERVERWATCH_RUNTIME_GID" == "$(id -g)" ]]\n'
        '[[ "$SERVERWATCH_API_IMAGE" == ghcr.io/example/serverwatch-api@sha256:* ]]\n'
        '[[ "$SERVERWATCH_WEB_IMAGE" == ghcr.io/example/serverwatch-web@sha256:* ]]\n'
        'printf "docker %s\n" "$*" >> "$CALLS"\n'
        'if [[ "$*" == *" port web 80" ]]; then echo "127.0.0.1:8080"; fi\n',
    )
    command(
        directory,
        "curl",
        'printf "curl %s\n" "$*" >> "$CALLS"\n'
        'if [[ "$*" == *"/api/v1/health"* ]]; then\n'
        '  printf \'{"status":"%s"}\n\' "${HEALTH:-healthy}"\n'
        "fi\n",
    )
    return state, {
        **os.environ,
        "HOME": str(tmp_path),
        "PATH": f"{directory}:{os.environ['PATH']}",
        "CALLS": str(tmp_path / "calls"),
    }


def invoke(script, env, *args):
    return subprocess.run(
        ["bash", str(script), *args],
        check=False,
        env=env,
        timeout=10,
        text=True,
        capture_output=True,
    )


def test_deploy_pulls_matching_images_and_records_only_verified_release(host):
    state, env = host
    result = invoke(DEPLOY, env, "staging", REVISION, API_IMAGE, WEB_IMAGE)
    assert result.returncode == 0, result.stderr
    calls = Path(env["CALLS"]).read_text()
    assert "git show " + REVISION + ":compose.yaml" in calls
    assert (state / f"compose-{REVISION}.yaml").read_text() == "reviewed-compose\n"
    assert "pull api migrate web" in calls
    assert "up -d --no-build --wait" in calls
    assert "curl --noproxy" in calls and "/docs" in calls
    assert (state / "previous-success").read_text() == "previous\n"
    assert (state / "last-success").read_text().splitlines() == [
        REVISION,
        API_IMAGE,
        WEB_IMAGE,
    ]


@pytest.mark.parametrize(
    ("target", "var", "value", "reason"),
    [
        ("production", "HEALTH", "healthy", "environment marker"),
        ("staging", "STALE", "1", "reachable from origin/main"),
        ("staging", "HEALTH", "unhealthy", "did not report healthy"),
    ],
)
def test_failed_release_keeps_previous_success(host, target, var, value, reason):
    state, env = host
    result = invoke(DEPLOY, {**env, var: value}, target, REVISION, API_IMAGE, WEB_IMAGE)
    assert result.returncode == 1
    assert reason in result.stderr
    assert (state / "last-success").read_text() == "previous\n"


def test_runner_rejects_remote_shell_syntax_before_ssh():
    env = {
        **os.environ,
        "DEPLOY_HOST": "example.invalid",
        "DEPLOY_USER": "deployment",
        "DEPLOY_SSH_KEY": "dummy-key",
        "DEPLOY_KNOWN_HOSTS": "dummy-pinned-host",
    }
    result = invoke(SSH, env, "staging", REVISION, API_IMAGE, "web;echo invalid")
    assert result.returncode == 1
    assert "Invalid deployment argument." in result.stderr
    assert "dummy-key" not in result.stdout + result.stderr
