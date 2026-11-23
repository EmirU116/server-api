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


def test_compose_preparation_preserves_private_files(tmp_path):
    directory = tmp_path / "private files"
    command = ["bash", str(SETUP), str(directory)]
    subprocess.run(command, check=True, capture_output=True, timeout=10)
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    files = {path.name: path.read_bytes() for path in directory.iterdir()}
    assert len({files[f"{role}_token"] for role in ("reader", "collector", "admin")}) == 3
    assert json.loads(files["host_identity.json"])["hostname"]
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in directory.iterdir())

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
    if not shutil.which("docker") or subprocess.run(
        ["docker", "compose", "version"], check=False, capture_output=True, timeout=10
    ).returncode:
        pytest.skip("Docker Compose plugin is unavailable")

    result = subprocess.run(
        ["docker", "compose", "--env-file", os.devnull, "-f",
         str(ROOT / "compose.yaml"), "config", "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
        env={key: value for key, value in os.environ.items() if not key.startswith("SERVERWATCH_")},
    )
    config = json.loads(result.stdout)
    services = config["services"]
    assert set(services) == {"api", "db", "migrate", "web"}
    for name in ("db", "api", "migrate"):
        assert not services[name].get("ports")
    assert services["web"]["ports"][0]["host_ip"] == "127.0.0.1"
    assert services["api"]["depends_on"]["migrate"]["condition"] == "service_completed_successfully"
    assert services["db"]["volumes"][0]["source"] == "postgres_data"
    assert config["networks"]["database"]["internal"]
    assert "db_admin_password" not in {secret["source"] for secret in services["api"]["secrets"]}
