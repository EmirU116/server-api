"""Exercise the web verifier with scripted HTTP responses."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "script",
    [
        "setup.sh",
        "infrastructure/bootstrap/setup_ubuntu_web.sh",
        "scripts/verification/verify_ubuntu_web.sh",
    ],
)
def test_web_scripts_require_an_address(script):
    result = subprocess.run(
        ["bash", str(ROOT / script)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 1
    assert "Supply the EC2 public IPv4 address" in result.stderr


def test_full_setup_runs_preflight_before_changes(tmp_path):
    boot = tmp_path / "infrastructure" / "bootstrap"
    boot.mkdir(parents=True)
    trace = tmp_path / "trace"
    (boot / "setup_ubuntu_web.sh").write_text(
        'echo "web:$SERVERWATCH_FULL_SETUP:$*" >> "$TRACE"\n'
    )
    (boot / "setup_ubuntu_monitoring.sh").write_text(
        'echo "monitor:$SERVERWATCH_FULL_SETUP:$1" >> "$TRACE"\n'
    )
    subprocess.run(
        ["bash", str(ROOT / "setup.sh"), "192.0.2.1"],
        check=True,
        env={
            **os.environ,
            "SERVERWATCH_PROJECT_DIR": str(tmp_path),
            "SERVERWATCH_FULL_SETUP": "",
            "TRACE": str(trace),
        },
        timeout=10,
    )
    assert trace.read_text().splitlines() == [
        "web:1:--preflight 192.0.2.1",
        f"monitor:1:{tmp_path}",
        "web:1:192.0.2.1",
    ]


@pytest.mark.parametrize(
    ("bad_schema", "expected", "message"),
    [(False, 0, "[PASS] Nginx"), (True, 1, "OpenAPI did not describe")],
)
def test_web_verifier(tmp_path, bad_schema, expected, message):
    scripts = tmp_path / "scripts" / "verification"
    scripts.mkdir(parents=True)
    verifier = scripts / "verify_ubuntu_web.sh"
    shutil.copyfile(ROOT / "scripts/verification/verify_ubuntu_web.sh", verifier)
    (scripts / "verify_ubuntu_monitoring.sh").write_text("exit 0\n")
    venv_bin = tmp_path / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    python = venv_bin / "python"
    python.write_text("#!/bin/bash\necho 17\n")
    python.chmod(0o755)
    curl = tmp_path / "curl"
    schema = "{}" if bad_schema else '{"paths":{"/api/v1/health":{}}}'
    curl.write_text(
        "#!/bin/bash\n"
        '[[ "$*" == *192.0.2.1:80:127.0.0.1* ]] || exit 1\n'
        'case "${!#}" in\n'
        """    */) echo '<script src="/assets/index.js"></script>' ;;\n"""
        "    */assets/index.js) echo 'console.log(1)' ;;\n"
        "    */docs) echo 'SwaggerUIBundle /openapi.json' ;;\n"
        f"    */openapi.json) echo '{schema}' ;;\n"
        """    */api/v1/health[?]server_id=17) echo '{"status":"healthy"}' ;;\n"""
        "    *) exit 1 ;;\nesac\n"
    )
    curl.chmod(0o755)
    result = subprocess.run(
        ["bash", str(verifier), "192.0.2.1"],
        check=False,
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == expected
    assert message in result.stdout + result.stderr
