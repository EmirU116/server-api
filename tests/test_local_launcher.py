"""Test launcher dispatch and safe preflight checks without Windows services."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts/setup/start_local.sh"
CHECKER = ROOT / "scripts/setup/check_local.py"


@pytest.mark.parametrize(
    "arguments,status", [(["--help"], 0), (["--bad"], 1), (["--postgres-service"], 1)]
)
def test_help_and_invalid_arguments(arguments, status):
    result = subprocess.run(
        ["bash", str(LAUNCHER), *arguments],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == status
    assert "Usage:" in result.stdout + result.stderr or "requires" in result.stderr


@pytest.mark.parametrize(
    "platform,converter", [("MINGW64_NT", "cygpath"), ("Linux", "wslpath")]
)
@pytest.mark.parametrize("status", [0, 7])
def test_windows_dispatch_preserves_paths_and_service_name(
    tmp_path, platform, converter, status
):
    project = tmp_path / "project with spaces/scripts/setup"
    project.mkdir(parents=True)
    launcher = project / "start_local.sh"
    shutil.copyfile(LAUNCHER, launcher)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    commands = {
        "uname": f"#!/bin/bash\nprintf '%s\\n' '{platform}'\n",
        converter: (
            "#!/bin/bash\nprintf '%s\\n' "
            "'D:\\project with spaces\\scripts\\setup\\start_local_windows.ps1'\n"
        ),
        "powershell.exe": f"#!/bin/bash\nprintf '<%s>\\n' \"$@\"\nexit {status}\n",
    }
    for name, content in commands.items():
        path = bin_dir / name
        path.write_text(content)
        path.chmod(0o755)
    result = subprocess.run(
        ["bash", str(launcher), "--postgres-service", "postgresql-x64-18"],
        env={"PATH": f"{bin_dir}:/usr/bin:/bin"},
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == status
    assert "<-File>" in result.stdout
    assert (
        "<D:\\project with spaces\\scripts\\setup\\start_local_windows.ps1>"
        in result.stdout
    )
    assert "<-PostgresService>\n<postgresql-x64-18>" in result.stdout


@pytest.mark.parametrize(
    "override,expected",
    [
        ({}, 0),
        ({"SERVERWATCH_DATABASE_HOST": "remote.invalid"}, 1),
        ({"SERVERWATCH_READER_TOKEN": ""}, 1),
        ({"SERVERWATCH_DATABASE_PASSWORD": ""}, 1),
        ({"SERVERWATCH_DATABASE_PORT": "bad-port"}, 1),
        ({"SERVERWATCH_ENVIRONMENT": "production"}, 1),
    ],
)
def test_configuration_checks_use_only_dummy_private_file(tmp_path, override, expected):
    config = {
        "SERVERWATCH_DATABASE_PASSWORD": "dummy-sensitive-password",
        "SERVERWATCH_READER_TOKEN": "dummy-sensitive-reader",
        **override,
    }
    env_file = tmp_path / "fake.env"
    env_file.write_text("\n".join(f"{name}={value}" for name, value in config.items()))
    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--env-file",
            str(env_file),
            "--configuration-only",
        ],
        env={
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        },
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == expected
    assert "dummy-sensitive" not in result.stdout + result.stderr


def test_missing_private_configuration_gives_feedback(tmp_path):
    result = subprocess.run(
        [sys.executable, str(CHECKER), "--env-file", str(tmp_path / "absent")],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 1
    assert "FAIL:" in result.stderr
    assert "Traceback" not in result.stderr
