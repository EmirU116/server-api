"""Exercise the continuous-deployment scripts and workflow with scripted commands."""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = "scripts/deployment/deploy_image.sh"
AUTHORIZE = "scripts/deployment/authorize_deploy_key.sh"
WORKFLOW = ROOT / ".github/workflows/deploy.yml"
REPOSITORY = "ghcr.io/owner/repo"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def fake_command(directory, name, body):
    path = directory / name
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(0o755)


def git(*args, cwd):
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **GIT_ENV},
    )
    return result.stdout.strip()


def commit(repo, name):
    (repo / name).write_text(name)
    git("add", name, cwd=repo)
    git("commit", "--quiet", "-m", name, cwd=repo)
    return git("rev-parse", "HEAD", cwd=repo)


@pytest.fixture
def host(tmp_path):
    """A GitHub stand-in, a host checkout of it, and fake host commands."""
    origin = tmp_path / "origin"
    origin.mkdir()
    git("init", "--quiet", "--initial-branch=main", cwd=origin)
    commit(origin, "first")
    project = tmp_path / "home/serverwatch"
    git("clone", "--quiet", str(origin), str(project), cwd=tmp_path)
    for name in (DEPLOY, AUTHORIZE):
        target = project / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    # Keep the copied scripts out of `git diff` without committing them.
    (project / ".git/info/exclude").write_text("scripts/\n")
    settings = tmp_path / "home/.config/serverwatch-delivery"
    settings.mkdir(parents=True)
    (settings / "compose.env").write_text(
        "SERVERWATCH_WEB_PORT=8080\nSERVERWATCH_API_IMAGE=ghcr.io/owner/repo/api:old\n"
    )
    # compose_host.sh is replaced by a recorder; its own tests cover it.
    (project / "scripts/deployment/compose_host.sh").write_text(
        'echo "$* | $SERVERWATCH_API_IMAGE $SERVERWATCH_WEB_IMAGE" >> "$TRACE"\n'
        '[[ "$*" != "port web 80" ]] || echo 127.0.0.1:8080\n'
        '[[ "$*" != "pull api web" || -z "$PULL_FAILS" ]] || exit 1\n'
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_command(bin_dir, "curl", 'echo "{\\"status\\":\\"${HEALTH:-healthy}\\"}"\n')
    fake_command(
        bin_dir,
        "docker",
        'if [[ "$1 $2" == "image ls" ]]; then\n'
        f'    printf "%s\\n" {REPOSITORY}/api:old {REPOSITORY}/web:"$KEEP" postgres:17\n'
        "else\n"
        '    echo "docker $*" >> "$TRACE"\n'
        "fi\n",
    )
    return {"tmp": tmp_path, "origin": origin, "project": project, "bin": bin_dir}


def deploy(host, *args, **env):
    environment = {
        **os.environ,
        **GIT_ENV,
        "HOME": str(host["tmp"] / "home"),
        "TRACE": str(host["tmp"] / "trace"),
        "PATH": f"{host['bin']}:{os.environ['PATH']}",
        **env,
    }
    return subprocess.run(
        ["bash", str(host["project"] / DEPLOY), *args],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        timeout=20,
    )


def trace(host):
    path = host["tmp"] / "trace"
    return path.read_text().splitlines() if path.exists() else []


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ([], "Supply the image repository and the commit SHA"),
        (["docker.io/owner/repo", "a" * 40], "ghcr.io/owner/repo"),
        (["ghcr.io/Owner/repo", "a" * 40], "in lowercase"),
        ([REPOSITORY, "main"], "40-character commit SHA"),
        ([REPOSITORY, "a" * 40 + "; rm -rf /"], "40-character commit SHA"),
    ],
)
def test_deploy_rejects_invalid_arguments(host, args, message):
    result = deploy(host, *args)
    assert result.returncode == 1
    assert message in result.stderr
    assert trace(host) == []


def test_deploy_pulls_the_commit_images_and_checks_health(host):
    sha = commit(host["origin"], "second")
    # GitHub sends the SHA as the SSH command; the forced command adds the rest.
    result = deploy(host, REPOSITORY, SSH_ORIGINAL_COMMAND=sha, KEEP=sha)
    assert result.returncode == 0, result.stderr
    assert f"[PASS] Deployed {sha}" in result.stdout
    assert git("rev-parse", "HEAD", cwd=host["project"]) == sha
    images = f"{REPOSITORY}/api:{sha} {REPOSITORY}/web:{sha}"
    assert trace(host) == [
        f"prepare | {images}",
        f"pull api web | {images}",
        f"up -d --no-build --wait | {images}",
        f"port web 80 | {images}",
        f"docker image rm {REPOSITORY}/api:old",
    ]
    settings = host["tmp"] / "home/.config/serverwatch-delivery"
    assert (settings / "deployed-commit").read_text() == f"{sha}\n"
    # Later manual Compose commands keep using the deployed images.
    assert (settings / "compose.env").read_text().splitlines() == [
        "SERVERWATCH_WEB_PORT=8080",
        f"SERVERWATCH_API_IMAGE={REPOSITORY}/api:{sha}",
        f"SERVERWATCH_WEB_IMAGE={REPOSITORY}/web:{sha}",
    ]
    assert (settings / "compose.env").stat().st_mode & 0o777 == 0o600


def test_deploy_refuses_a_commit_that_is_not_on_main(host):
    git("switch", "--quiet", "-c", "feature", cwd=host["origin"])
    sha = commit(host["origin"], "unmerged")
    result = deploy(host, REPOSITORY, sha)
    assert result.returncode == 1
    assert "is not on origin/main" in result.stderr
    assert trace(host) == []


def test_deploy_refuses_a_checkout_with_local_changes(host):
    sha = commit(host["origin"], "second")
    (host["project"] / "first").write_text("edited on the server")
    result = deploy(host, REPOSITORY, sha)
    assert result.returncode == 1
    assert "uncommitted changes" in result.stderr
    assert trace(host) == []


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"PULL_FAILS": "1"}, "Check that both GHCR packages are public"),
        ({"HEALTH": "degraded"}, "did not report healthy"),
    ],
)
def test_deploy_reports_failures_without_recording_the_commit(host, env, message):
    sha = commit(host["origin"], "second")
    result = deploy(host, REPOSITORY, sha, **env)
    assert result.returncode == 1
    assert message in result.stderr
    assert not (
        host["tmp"] / "home/.config/serverwatch-delivery/deployed-commit"
    ).exists()


def authorize(host, key_text, groups="ubuntu docker"):
    key = host["tmp"] / "github_deploy.pub"
    key.write_text(key_text)
    host_key = host["tmp"] / "ssh_host_ed25519_key.pub"
    host_key.write_text("ssh-ed25519 HOSTKEY root@host\n")
    fake_command(
        host["bin"],
        "id",
        f'case "$1" in -nG) echo "{groups}" ;; -un) echo ubuntu ;; *) echo 1000 ;; esac\n',
    )
    git(
        "remote",
        "set-url",
        "origin",
        "git@github.com:Owner/Server-API.git",
        cwd=host["project"],
    )
    return subprocess.run(
        ["bash", str(host["project"] / AUTHORIZE), str(key), "serverwatch.dev"],
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "HOME": str(host["tmp"] / "home"),
            "PATH": f"{host['bin']}:{os.environ['PATH']}",
            "SERVERWATCH_SSH_HOST_KEY_FILE": str(host_key),
        },
        timeout=10,
    )


def test_authorize_restricts_the_key_to_the_deploy_script(host):
    first = authorize(host, "ssh-ed25519 AAAAKEY github-deploy\n")
    again = authorize(host, "ssh-ed25519 AAAAKEY github-deploy\n")
    assert first.returncode == 0, first.stderr
    assert again.returncode == 0, again.stderr
    authorized = host["tmp"] / "home/.ssh/authorized_keys"
    script = host["project"] / DEPLOY
    expected = f'restrict,command="bash {script} ghcr.io/owner/server-api" ssh-ed25519 AAAAKEY github-deploy'
    assert authorized.read_text().splitlines() == [expected]
    assert authorized.stat().st_mode & 0o777 == 0o600
    assert (
        "SERVERWATCH_DEPLOY_KNOWN_HOSTS  serverwatch.dev ssh-ed25519 HOSTKEY"
        in again.stdout
    )


@pytest.mark.parametrize(
    ("key_text", "groups", "message"),
    [
        ("ssh-rsa AAAAKEY\n", "ubuntu docker", "must be an ssh-ed25519 public key"),
        (
            'command="sh" ssh-ed25519 AAAAKEY\n',
            "ubuntu docker",
            "must be an ssh-ed25519 public key",
        ),
        ("ssh-ed25519 A\nssh-ed25519 B\n", "ubuntu docker", "exactly one public key"),
        ("ssh-ed25519 AAAAKEY\n", "ubuntu", "not in the docker group"),
    ],
)
def test_authorize_rejects_unsafe_keys_and_users(host, key_text, groups, message):
    result = authorize(host, key_text, groups)
    assert result.returncode == 1
    assert message in result.stderr
    assert not (host["tmp"] / "home/.ssh/authorized_keys").exists()


def test_workflow_deploys_only_after_ci_on_main_and_keeps_secrets_out_of_commands():
    workflow = WORKFLOW.read_text()
    ci_name = re.search(
        r"^name: (.+)$", (ROOT / ".github/workflows/ci.yml").read_text(), re.MULTILINE
    )
    assert f"workflows: [{ci_name.group(1)}]" in workflow
    assert "branches: [main]" in workflow
    assert "github.event.workflow_run.conclusion == 'success'" in workflow
    assert "vars.SERVERWATCH_DEPLOY_ENABLED == 'true'" in workflow
    assert "needs: images" in workflow
    assert "StrictHostKeyChecking=yes" in workflow
    # Secrets reach commands only through environment variables.
    run_blocks = re.findall(r"run: \|\n((?:          .*\n)+)", workflow)
    assert run_blocks
    assert all("${{" not in block for block in run_blocks)
