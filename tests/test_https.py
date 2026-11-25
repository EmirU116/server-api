"""Exercise the custom-domain HTTPS setup and verifier with scripted commands."""

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "infrastructure/bootstrap/setup_https.sh"
VERIFY = ROOT / "scripts/verification/verify_https.sh"
NGINX = ROOT / "infrastructure/nginx"


def fake_command(directory, name, body):
    path = directory / name
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(0o755)


def run(args, path_dir=None, env=None):
    environment = {**os.environ, **(env or {})}
    if path_dir is not None:
        environment["PATH"] = f"{path_dir}:{environment['PATH']}"
    return subprocess.run(
        ["bash", *map(str, args)],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        timeout=10,
    )


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ([], "Supply the domain and the EC2 public IPv4 address"),
        (["https://example.com", "192.0.2.1"], "without a scheme"),
        (["example.com/docs", "192.0.2.1"], "without a scheme"),
        (["www.example.com", "192.0.2.1"], "without www"),
        (["example.com", "not-an-ip"], "IPv4 address"),
    ],
)
def test_setup_rejects_invalid_arguments(args, message):
    result = run([SETUP, "--preflight", *args])
    assert result.returncode == 1
    assert message in result.stderr


def test_setup_stops_when_dns_points_elsewhere(tmp_path):
    fake_command(tmp_path, "getent", 'echo "198.51.100.7 STREAM $2"\n')
    result = run([SETUP, "--preflight", "example.com", "192.0.2.1"], tmp_path)
    assert result.returncode == 1
    assert "DNS for example.com does not point to 192.0.2.1" in result.stderr


def test_preflight_accepts_a_domain_pointing_here(tmp_path):
    fake_command(tmp_path, "getent", 'echo "192.0.2.1 STREAM $2"\n')
    result = run([SETUP, "--preflight", "Example.COM", "192.0.2.1"], tmp_path)
    assert result.returncode == 0, result.stderr


def test_setup_runs_https_preflight_first_and_https_last(tmp_path):
    boot = tmp_path / "infrastructure" / "bootstrap"
    boot.mkdir(parents=True)
    trace = tmp_path / "trace"
    for name in ("setup_ubuntu_web.sh", "setup_ubuntu_monitoring.sh", "setup_https.sh"):
        (boot / name).write_text(f'echo "{name}:$*" >> "$TRACE"\n')
    result = run(
        [ROOT / "setup.sh", "192.0.2.1"],
        env={
            "SERVERWATCH_PROJECT_DIR": str(tmp_path),
            "SERVERWATCH_DOMAIN": "example.com",
            "TRACE": str(trace),
            "HOME": str(tmp_path),
        },
    )
    assert result.returncode == 0, result.stderr
    assert trace.read_text().splitlines() == [
        "setup_ubuntu_web.sh:--preflight 192.0.2.1",
        "setup_https.sh:--preflight example.com 192.0.2.1",
        f"setup_ubuntu_monitoring.sh:{tmp_path}",
        "setup_ubuntu_web.sh:192.0.2.1",
        "setup_https.sh:example.com 192.0.2.1",
    ]


@pytest.mark.parametrize(
    ("redirect", "expected", "message"),
    [
        ("301 https://example.com/docs", 0, "[PASS] example.com serves"),
        ("200 ", 1, "HTTP did not redirect to HTTPS"),
    ],
)
def test_https_verifier(tmp_path, redirect, expected, message):
    fake_command(
        tmp_path,
        "curl",
        '[[ "$*" == *"example.com:443:127.0.0.1"* ]] || exit 1\n'
        '[[ "$*" != *--insecure* ]] || exit 1\n'
        'case "${!#}" in\n'
        '    https://example.com/api/v1/health*) echo \'{"status":"healthy"}\' ;;\n'
        "    https://example.com/docs) echo 'SwaggerUIBundle' ;;\n"
        f"    http://example.com/docs) printf '%s' '{redirect}' ;;\n"
        "    *) exit 22 ;;\n"
        "esac\n",
    )
    result = run([VERIFY, "example.com"], tmp_path)
    assert result.returncode == expected, result.stderr
    assert message in (result.stdout + result.stderr)


def locations(config):
    """Return the location blocks, which must match between the two sites."""
    return re.findall(r"    location .*?\n    }\n", config, re.DOTALL)


def test_https_site_serves_the_same_routes_as_the_http_site():
    http_site = (NGINX / "serverwatch.conf").read_text()
    https_site = (NGINX / "serverwatch-domain-https.conf").read_text()
    assert len(locations(http_site)) == 3
    assert locations(https_site) == locations(http_site)


def test_domain_http_site_only_answers_the_certificate_check():
    site = (NGINX / "serverwatch-domain-http.conf").read_text()
    assert "location /.well-known/acme-challenge/" in site
    assert "return 301 https://$host$request_uri;" in site
    assert "proxy_pass" not in site
