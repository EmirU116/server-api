"""Exercise Bash reporting with fake systemd/HTTP responses, never a real EC2."""

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOST = {
    "hostname": "dummy-ec2",
    "os_type": "Linux",
    "os_name": "Ubuntu",
    "os_version": "24.04",
    "architecture": "x86_64",
}


@pytest.fixture
def deployment(tmp_path):
    """Keep all credentials, command substitutes, and host files temporary."""
    project = tmp_path / "project"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    python = project / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text(
        "#!/bin/bash\n"
        'if [[ "${1:-}" == "-m" || "${1:-}" == "-c" ]]; then exit 0; fi\n'
        f'exec {shlex.quote(sys.executable)} "$@"\n'
    )
    python.chmod(0o755)
    source = project / "backend/app/services/server.py"
    source.parent.mkdir(parents=True)
    source.write_text(f"def read_host_info():\n    return {HOST!r}\n")
    token = tmp_path / "home/.config/serverwatch-ec2-test/reader_token"
    token.parent.mkdir(parents=True)
    token.write_text("dummy-private-token")
    token.chmod(0o600)

    systemctl = bin_dir / "systemctl"
    systemctl.write_text("#!/bin/bash\nexit 0\n")
    systemctl.chmod(0o755)
    curl = bin_dir / "curl"
    curl.write_text(
        f"#!{sys.executable}\n"
        + """
import json
import os
from pathlib import Path
import sys
args = sys.argv[1:]
url = args[-1]
authenticated = "--config" in args
if authenticated:
    sys.stdin.read()  # Consume the private header without printing it.
status = 400
data = {}
if "/server" in url:
    if not authenticated:
        status = 401
    elif "server_id=-1" in url:
        status = 400
    elif "server_id=2" in url:
        status = 404
    elif "verbose=true" in url:
        status = 422
    else:
        status = 500 if os.environ.get("BROKEN_SERVER") else 200
        data = {"id": 1, "name": "ServerWatch EC2 test", **json.loads(os.environ["FAKE_HOST"])}
elif "server_id=2" in url:
    status = 404
elif "server_id=1" in url:
    status = 503
    data = {"server_id": 1, "status": "unhealthy", "checks": {"server": "up", "database": "down"}}
if "--output" in args:
    Path(args[args.index("--output") + 1]).write_text(json.dumps(data))
if "--write-out" in args:
    print(status, end="")
"""
    )
    curl.chmod(0o755)
    environment = {
        **os.environ,
        "HOME": str(tmp_path / "home"),
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "FAKE_HOST": json.dumps(HOST),
    }
    environment.pop("BROKEN_SERVER", None)
    return project, token, environment


@pytest.mark.parametrize(
    "scenario", ["healthy_setup", "broken_server", "missing_token"]
)
def test_verification_reports_success_and_failures(deployment, scenario):
    project, token, environment = deployment
    if scenario == "broken_server":
        environment["BROKEN_SERVER"] = "1"
    if scenario == "missing_token":
        token.unlink()

    result = subprocess.run(
        ["bash", str(ROOT / "scripts/verification/verify_ec2.sh"), str(project)],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert "dummy-private-token" not in result.stdout + result.stderr
    assert "[SUMMARY]" in result.stdout
    if scenario == "healthy_setup":
        # This verifier intentionally targets native Ubuntu; other hosts fail.
        native_ubuntu = "ID=ubuntu" in Path("/etc/os-release").read_text()
        native_ubuntu = native_ubuntu and not Path("/.dockerenv").exists()
        native_ubuntu = native_ubuntu and not Path("/run/.containerenv").exists()
        assert result.returncode == (0 if native_ubuntu else 1)
        assert "[PASS] Server explicit selection (HTTP 200)" in result.stdout
        assert "structured health 503 is expected" in result.stdout
    else:
        assert result.returncode == 1
        assert "[FAIL]" in result.stdout
        if scenario == "broken_server":
            assert "expected 200, received 500" in result.stdout
        else:
            assert "Authenticated server checks skipped" in result.stdout
