"""Check private Compose setup and the published network/service configuration."""

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "scripts/setup/prepare_compose.sh"
HOST = ROOT / "scripts/deployment/compose_host.sh"
# prepare_compose.sh imports these from its own checkout.
PREPARE_FILES = (
    "scripts/setup/prepare_compose.sh",
    "scripts/setup/private_files.py",
    "backend/app/__init__.py",
    "backend/app/host_identity.py",
)


def copy_prepare_files(project: Path) -> None:
    for name in PREPARE_FILES:
        (project / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, project / name)


def test_start_creates_private_defaults_and_collect_uses_the_published_port(tmp_path):
    project = tmp_path / "serverwatch"
    copy_prepare_files(project)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text(
        "#!/bin/bash\n"
        'case "$*" in\n'
        '  "info "*) ;;\n'
        '  *" config --format json")\n'
        '    printf \'{"secrets":{"db_password":{"file":"%s/db_password"}}}\\n\' '
        '"$HOME/.config/serverwatch-compose/secrets" ;;\n'
        '  *" up -d --build --wait"|*" ps -a") printf "%s\\n" "$*" ;;\n'
        '  *" port web 80") echo 127.0.0.1:8197 ;;\n'
        "  *) exit 1 ;;\n"
        "esac\n"
    )
    docker.chmod(0o755)
    environment = {**os.environ, "HOME": str(tmp_path)}
    environment["PATH"] = f"{bin_dir}:{environment['PATH']}"
    command = ["bash", str(HOST)]
    result = subprocess.run(
        [*command, "start"],
        env=environment,
        check=True,
        capture_output=True,
        timeout=10,
    )
    assert b"up -d --build --wait" in result.stdout
    assert b"ps -a" in result.stdout
    config = tmp_path / ".config/serverwatch-delivery/compose.env"
    assert stat.S_IMODE(config.stat().st_mode) == 0o600
    assert config.read_text().splitlines() == [
        "SERVERWATCH_WEB_PORT=8080",
        'SERVERWATCH_COMPOSE_SECRETS="${HOME}/.config/serverwatch-compose/secrets"',
    ]
    config.write_text(config.read_text().replace("8080", "8197"))
    existing = config.read_bytes()
    python = project / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text(
        '#!/bin/bash\nif [[ "$1" == -c ]]; then exit 0; fi\nprintf "%s\\n" "$@"\n'
    )
    python.chmod(0o755)
    subprocess.run(
        [*command, "start"],
        env=environment,
        check=True,
        capture_output=True,
        timeout=10,
    )
    assert config.read_bytes() == existing
    result = subprocess.run(
        [*command, "collect"],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.stdout.splitlines() == [
        str(project / "scripts/monitoring/collect_local.py"),
        "--env-file",
        str(tmp_path / ".config/serverwatch-compose/secrets/collector.env"),
        "--api-port",
        "8197",
    ]


def test_compose_preparation_preserves_private_files(tmp_path):
    directory = tmp_path / "private files"
    command = ["bash", str(SETUP), str(directory)]
    subprocess.run(command, check=True, capture_output=True, timeout=10)
    assert (directory / "db_migration_password").is_file()
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    files = {path.name: path.read_bytes() for path in directory.iterdir()}
    assert (
        len({files[f"{role}_token"] for role in ("reader", "collector", "admin")}) == 3
    )
    assert json.loads(files["host_identity.json"])["hostname"]
    assert all(
        stat.S_IMODE(path.stat().st_mode) == 0o600 for path in directory.iterdir()
    )

    rerun = subprocess.run(command, check=True, capture_output=True, timeout=10)
    assert files == {path.name: path.read_bytes() for path in directory.iterdir()}
    assert all(value.strip() not in rerun.stdout for value in files.values())


def test_compose_preparation_rejects_symlink(tmp_path):
    directory = tmp_path / "private"
    directory.mkdir(mode=0o700)
    target = tmp_path / "unrelated"
    target.write_text("unchanged", encoding="utf-8")
    (directory / "db_admin_password").symlink_to(target)

    result = subprocess.run(
        ["bash", str(SETUP), str(directory)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "must not be a symlink" in result.stderr
    assert target.read_text(encoding="utf-8") == "unchanged"


def test_compose_config_only_publishes_web(tmp_path):
    if (
        not shutil.which("docker")
        or subprocess.run(
            ["docker", "compose", "version"],
            check=False,
            capture_output=True,
            timeout=10,
        ).returncode
    ):
        pytest.skip("Docker Compose plugin is unavailable")

    result = subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            os.devnull,
            "-f",
            str(ROOT / "compose.yaml"),
            "config",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
        env={
            key: value
            for key, value in os.environ.items()
            if not key.startswith("SERVERWATCH_")
        },
    )
    config = json.loads(result.stdout)
    services = config["services"]
    assert set(services) == {"api", "db", "migrate", "web"}
    for name in ("db", "api", "migrate"):
        assert not services[name].get("ports")
    assert services["web"]["ports"][0]["host_ip"] == "127.0.0.1"
    assert (
        services["api"]["depends_on"]["migrate"]["condition"]
        == "service_completed_successfully"
    )
    assert services["db"]["volumes"][0]["source"] == "postgres_data"
    assert config["networks"]["database"]["internal"]
    assert "db_admin_password" not in {
        secret["source"] for secret in services["api"]["secrets"]
    }


def test_host_config_resolves_custom_port_and_external_secrets(tmp_path):
    if (
        not shutil.which("docker")
        or subprocess.run(
            ["docker", "compose", "version"],
            check=False,
            capture_output=True,
            timeout=10,
        ).returncode
    ):
        pytest.skip("Docker Compose plugin is unavailable")

    project = tmp_path / "serverwatch"
    project.mkdir()
    shutil.copyfile(ROOT / "compose.yaml", project / "compose.yaml")
    state = tmp_path / ".config/serverwatch-delivery"
    state.mkdir(parents=True)
    directory = tmp_path / "external secrets"
    (state / "compose.env").write_text(
        f"SERVERWATCH_WEB_PORT=8197\nSERVERWATCH_COMPOSE_SECRETS='{directory}'\n"
    )
    command = ["bash", str(ROOT / "scripts/deployment/compose_host.sh")]
    environment = {
        **os.environ,
        "HOME": str(tmp_path),
        "SERVERWATCH_WEB_PORT": "8888",
        "SERVERWATCH_COMPOSE_SECRETS": "/ignored",
    }
    copy_prepare_files(project)
    subprocess.run(
        [*command, "prepare"],
        env=environment,
        check=True,
        capture_output=True,
        timeout=10,
    )
    assert (directory / "db_migration_password").is_file()
    result = subprocess.run(
        [*command, "config", "--format", "json"],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    config = json.loads(result.stdout)
    assert config["services"]["web"]["ports"][0]["published"] == "8197"
    assert config["secrets"]["db_password"]["file"] == str(directory / "db_password")
    assert config["services"]["migrate"]["environment"][
        "SERVERWATCH_DATABASE_USER"
    ] == ("serverwatch_migrator")
    assert {item["source"] for item in config["services"]["api"]["secrets"]}.isdisjoint(
        {"db_admin_password", "db_migration_password"}
    )
