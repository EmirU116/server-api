"""Exercise release, trust and failure checks without registry access or SSH."""

import base64
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "scripts/deployment/deploy_compose.sh"
ENTRY = ROOT / "scripts/deployment/deploy_ssh_entry.sh"
SSH = ROOT / "scripts/deployment/ssh_compose.sh"
REVISION = "1" * 40
API_IMAGE = "ghcr.io/example/serverwatch-api@sha256:" + "a" * 64
WEB_IMAGE = "ghcr.io/example/serverwatch-web@sha256:" + "b" * 64
RELEASE = ("staging", REVISION, API_IMAGE, WEB_IMAGE)


def sign(key, release=RELEASE):
    result = subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "serverwatch-release-v1"],
        input="".join(f"{field}\n" for field in release).encode(),
        check=True,
        capture_output=True,
        timeout=10,
    )
    return base64.b64encode(result.stdout).decode()


def command(path, name, body):
    wrapper = path / name
    wrapper.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + body)
    wrapper.chmod(0o755)


@pytest.fixture
def host(tmp_path):
    directory = tmp_path / "bin"
    directory.mkdir()
    installed = tmp_path / "installed"
    installed.mkdir()
    for script in (DEPLOY, ENTRY, DEPLOY.with_name("compose_host.sh")):
        shutil.copyfile(script, installed / script.name)
    key = tmp_path / "test-signing-key"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
        check=True,
        timeout=10,
    )
    public_key = key.with_suffix(".pub").read_text()
    (installed / "release-signers").write_text(
        f'staging namespaces="serverwatch-release-v1" {public_key}'
    )
    (tmp_path / "serverwatch").mkdir()
    state = tmp_path / ".config/serverwatch-delivery"
    state.mkdir(parents=True)
    outside = tmp_path / "external secrets"
    outside.mkdir()
    (state / "compose.env").write_text(
        f"SERVERWATCH_WEB_PORT=8197\nSERVERWATCH_COMPOSE_SECRETS='{outside}'\n"
    )
    (state / "repository").write_text("ghcr.io/example/serverwatch\n")
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
        'printf "docker %s\n" "$*" >> "$CALLS"\n'
        '[[ -z "${SERVERWATCH_WEB_PORT+x}" && -z "${SERVERWATCH_COMPOSE_SECRETS+x}" ]]\n'
        '[[ "$6" == --env-file && "$7" == "$HOME/.config/serverwatch-delivery/compose.env" ]]\n'
        'source "$7"\n'
        '[[ "$SERVERWATCH_COMPOSE_SECRETS" == "$HOME/external secrets" ]]\n'
        '[[ "$SERVERWATCH_WEB_BIND" == 127.0.0.1 ]]\n'
        '[[ "$SERVERWATCH_RUNTIME_UID" == "$(id -u)" ]]\n'
        '[[ "$SERVERWATCH_RUNTIME_GID" == "$(id -g)" ]]\n'
        '[[ "$SERVERWATCH_API_IMAGE" == ghcr.io/example/serverwatch-api@sha256:* ]]\n'
        '[[ "$SERVERWATCH_WEB_IMAGE" == ghcr.io/example/serverwatch-web@sha256:* ]]\n'
        'if [[ "$*" == *" port web 80" ]]; then echo "127.0.0.1:$SERVERWATCH_WEB_PORT"; fi\n',
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
        "SERVERWATCH_WEB_PORT": "8888",
        "SERVERWATCH_COMPOSE_SECRETS": "/ignored",
        "CALLS": str(tmp_path / "calls"),
        "TEST_RELEASE_SIGNATURE": sign(key),
    }


def invoke(script, env, *args, request=None):
    if script in (DEPLOY, ENTRY):
        script = Path(env["HOME"]) / "installed" / script.name
    return subprocess.run(
        ["bash", str(script), *args],
        check=False,
        env=env,
        timeout=10,
        text=True,
        capture_output=True,
        input=request,
    )


def test_deploy_pulls_matching_images_and_records_only_verified_release(host):
    state, env = host
    result = invoke(
        ENTRY,
        env,
        request=f"serverwatch-deploy {' '.join(RELEASE)} {env['TEST_RELEASE_SIGNATURE']}\n",
    )
    assert result.returncode == 0, result.stderr
    calls = Path(env["CALLS"]).read_text()
    assert "git show " + REVISION + ":compose.yaml" in calls
    assert (state / f"compose-{REVISION}.yaml").read_text() == "reviewed-compose\n"
    assert "pull api migrate web" in calls
    assert "up -d --no-build --wait" in calls
    assert "curl --noproxy" in calls and "127.0.0.1:8197/docs" in calls
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
    result = invoke(
        DEPLOY, {**env, var: value}, target, *RELEASE[1:], env["TEST_RELEASE_SIGNATURE"]
    )
    assert result.returncode == 1
    assert reason in result.stderr
    assert (state / "last-success").read_text() == "previous\n"


@pytest.mark.parametrize(
    "release",
    [
        ("staging", "2" * 40, API_IMAGE, WEB_IMAGE),
        ("staging", REVISION, API_IMAGE[:-1] + "c", WEB_IMAGE),
        ("staging", REVISION, API_IMAGE, WEB_IMAGE[:-1] + "c"),
        ("production", REVISION, API_IMAGE, WEB_IMAGE),
    ],
)
def test_ssh_entry_rejects_a_release_that_differs_from_approval_before_docker(
    host, release
):
    state, env = host
    (state / "environment").write_text(f"{release[0]}\n")
    # Trust this test key for both principals to isolate the signed environment check.
    installed = Path(env["HOME"]) / "installed"
    public_key = (Path(env["HOME"]) / "test-signing-key.pub").read_text()
    (installed / "release-signers").write_text(f"staging,production {public_key}")
    result = invoke(
        ENTRY,
        env,
        request=f"serverwatch-deploy {' '.join(release)} {env['TEST_RELEASE_SIGNATURE']}\n",
    )
    assert result.returncode == 1
    assert "Release approval signature does not match" in result.stderr
    assert not Path(env["CALLS"]).exists()
    assert (state / "last-success").read_text() == "previous\n"


def test_ssh_entry_rejects_unsigned_release(host):
    _, env = host
    result = invoke(ENTRY, env, request=f"serverwatch-deploy {' '.join(RELEASE)}\n")
    assert result.returncode == 1
    assert "only accepts a ServerWatch deployment request" in result.stderr
    assert not Path(env["CALLS"]).exists()


def test_ssh_entry_rejects_signature_from_untrusted_key(host):
    _, env = host
    key = Path(env["HOME"]) / "unauthorized-key"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
        check=True,
        timeout=10,
    )
    request = f"serverwatch-deploy {' '.join(RELEASE)} {sign(key)}\n"
    result = invoke(ENTRY, env, request=request)
    assert result.returncode == 1
    assert "Release approval signature does not match" in result.stderr
    assert not Path(env["CALLS"]).exists()


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


@pytest.mark.parametrize(
    "request_text",
    [
        "id",
        "bash -s -- staging",
        f"serverwatch-deploy {' '.join(RELEASE)} {{signature}}; id",
        f"serverwatch-deploy {' '.join(RELEASE)} {{signature}}\nid",
    ],
)
def test_ssh_entry_rejects_arbitrary_commands_before_accessing_host(host, request_text):
    _, env = host
    result = invoke(
        ENTRY,
        env,
        request=request_text.format(signature=env["TEST_RELEASE_SIGNATURE"]) + "\n",
    )
    assert result.returncode == 1
    assert "only accepts a ServerWatch deployment request" in result.stderr
    assert not Path(env["CALLS"]).exists()


def test_ssh_entry_rejects_images_from_a_different_repository(host):
    _, env = host
    images = [image.replace("/example/", "/other/") for image in (API_IMAGE, WEB_IMAGE)]
    result = invoke(
        ENTRY,
        env,
        request=f"serverwatch-deploy staging {REVISION} {' '.join(images)} {env['TEST_RELEASE_SIGNATURE']}\n",
    )
    assert result.returncode == 1
    assert "host release repository" in result.stderr
    assert not Path(env["CALLS"]).exists()


def test_runner_requests_only_the_forced_entry_point(host):
    _, env = host
    directory = Path(env["HOME"]) / "bin"
    command(
        directory,
        "ssh",
        'printf "%s\n" "$@" > "$CALLS"\nif IFS= read -r ignored; then exit 1; fi\n',
    )
    env.update(
        DEPLOY_HOST="example.invalid",
        DEPLOY_USER="deployment",
        DEPLOY_SSH_KEY="test-key",
        DEPLOY_KNOWN_HOSTS=(
            "example.invalid "
            + (Path(env["HOME"]) / "test-signing-key.pub").read_text()
        ),
        DEPLOY_RELEASE_SIGNING_KEY=(Path(env["HOME"]) / "test-signing-key").read_text(),
    )
    result = invoke(SSH, env, "staging", REVISION, API_IMAGE, WEB_IMAGE, request="")
    assert result.returncode == 0, result.stderr
    args = Path(env["CALLS"]).read_text().splitlines()
    assert args[-7:-1] == [
        "deployment@example.invalid",
        "serverwatch-deploy",
        "staging",
        REVISION,
        API_IMAGE,
        WEB_IMAGE,
    ]
    assert "-n" in args and "-T" in args and "ClearAllForwardings=yes" in args
    result = invoke(ENTRY, env, request=" ".join(args[-6:]) + "\n")
    assert result.returncode == 0, result.stderr
