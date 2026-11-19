"""Ubuntu automation tests never install packages or manage host services."""

import importlib.util
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import SecretStr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


configure = load_module("ubuntu_setup", "scripts/setup/configure_ubuntu.py")
checker = load_module(
    "ubuntu_verify", "scripts/verification/check_ubuntu_monitoring.py"
)


@pytest.fixture(autouse=True)
def no_ambient_settings(monkeypatch):
    for name in list(os.environ):
        if name.startswith("SERVERWATCH_"):
            monkeypatch.delenv(name)


@pytest.fixture
def config(tmp_path):
    folder = tmp_path / "private"
    configure.prepare(folder)
    return folder


def test_configuration_is_private_and_reruns_preserve_everything(config):
    before = {path.name: path.read_bytes() for path in config.iterdir()}
    configure.prepare(config)
    assert before == {path.name: path.read_bytes() for path in config.iterdir()}
    assert config.stat().st_mode & 0o777 == 0o700
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in config.iterdir())
    assert (
        len(
            {
                (config / f"{role}_token").read_text()
                for role in ("reader", "collector", "admin")
            }
        )
        == 3
    )
    settings = configure.validate(config)
    assert settings.database_host == "127.0.0.1"
    assert settings.database_name == configure.DATABASE
    assert "db_password" not in (config / "collector.env").read_text()
    assert "admin_token" not in (config / "collector.env").read_text()


@pytest.mark.parametrize(
    "problem",
    [
        "permissions",
        "symlink",
        "duplicate",
        "remote",
        "missing",
        "collector",
        "directory",
    ],
)
def test_unsafe_configuration_is_rejected_without_replacing_files(
    config, tmp_path, problem
):
    token = config / "reader_token"
    if problem == "permissions":
        token.chmod(0o644)
    elif problem == "symlink":
        token.unlink()
        target = tmp_path / "target"
        target.write_text("dummy")
        token.symlink_to(target)
    elif problem == "duplicate":
        token.write_text((config / "admin_token").read_text())
    elif problem == "remote":
        path = config / "api.env"
        path.write_text(path.read_text().replace("127.0.0.1", "remote.example"))
    elif problem == "missing":
        token.unlink()
    elif problem == "collector":
        (config / "collector.env").write_text("SERVERWATCH_ADMIN_TOKEN=dummy\n")
    else:
        config.chmod(0o755)
    with pytest.raises((RuntimeError, FileNotFoundError)):
        configure.validate(config)


def test_database_sql_contains_verifier_not_plain_password(config):
    password = (config / "db_password").read_text().strip()
    sql = configure.database_sql(config)
    assert password not in sql
    assert "SCRAM-SHA-256$4096:" in sql
    assert "ALTER ROLE" not in sql and "DROP" not in sql
    assert "NOSUPERUSER" in sql and "NOCREATEDB" in sql
    assert "\\gexec" in repr(sql)


@pytest.mark.parametrize("address", ["127.0.0.1:5432", "[::1]:5432"])
def test_listeners_accept_only_loopback(monkeypatch, address):
    output = f"LISTEN 0 128 127.0.0.1:8000 0.0.0.0:*\nLISTEN 0 128 {address} *:*\n"
    monkeypatch.setattr(
        checker.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=output)
    )
    checker.check_listeners()


@pytest.mark.parametrize(
    "address", ["0.0.0.0:5432", "[::]:5432", "10.0.0.1:5432", "127.0.0.1:9999"]
)
def test_missing_or_public_listener_fails(monkeypatch, address):
    output = f"LISTEN 0 128 127.0.0.1:8000 *:*\nLISTEN 0 128 {address} *:*\n"
    monkeypatch.setattr(
        checker.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=output)
    )
    with pytest.raises(RuntimeError):
        checker.check_listeners()


@pytest.mark.parametrize(
    "scenario",
    ["fresh", "stale", "unhealthy", "unauthenticated", "storage_down", "wrong_host"],
)
def test_http_check_requires_real_fresh_persisted_sample(monkeypatch, scenario):
    import app.services.server

    host = {
        "hostname": "host",
        "os_type": "Linux",
        "os_name": "Ubuntu",
        "os_version": "24.04",
        "architecture": "x86_64",
    }
    monkeypatch.setattr(app.services.server, "read_host_info", lambda: host)
    monkeypatch.setattr(checker.time, "sleep", lambda _: None)
    calls = []
    ticks = iter(range(0, 100, 5))
    monkeypatch.setattr(checker.time, "monotonic", lambda: next(ticks))

    def request(path, token=None):
        calls.append(path)
        if path == "/server":
            if token is None:
                return (200 if scenario == "unauthenticated" else 401), {}
            return 200, {
                "id": 1,
                "name": "Ubuntu",
                **host,
                "hostname": "wrong" if scenario == "wrong_host" else "host",
            }
        if path == "/health?server_id=-1":
            return 400, {}
        if path.startswith("/health"):
            return (503 if scenario == "unhealthy" else 200), {
                "server_id": 1,
                "status": "healthy",
                "checks": {"server": "up", "database": "up"},
            }
        if path.startswith("/incidents"):
            return 200, {"items": []}
        if scenario == "storage_down":
            return 503, {}
        count = calls.count("/metrics?limit=1")
        collected = datetime.now(UTC)
        if scenario == "stale" or count == 1:
            collected -= timedelta(minutes=1)
        sample = {
            "id": str(uuid4()),
            "collected_at": collected.isoformat(),
            "cpu_percent": 1,
            "memory_percent": 2,
            "disk_percent": 3,
            "uptime_seconds": 4,
        }
        return 200, {"items": [sample], "total": 1, "limit": 1, "offset": 0}

    monkeypatch.setattr(checker, "request", request)
    settings = SimpleNamespace(
        reader_token=SecretStr("dummy-reader"), server_name="Ubuntu"
    )
    if scenario == "fresh":
        checker.check_http(settings)
        assert calls.count("/metrics?limit=1") >= 2
    else:
        with pytest.raises(RuntimeError):
            checker.check_http(settings)


@pytest.mark.parametrize(
    "script",
    [
        "infrastructure/bootstrap/setup_ubuntu_monitoring.sh",
        "scripts/verification/verify_ubuntu_monitoring.sh",
    ],
)
def test_bash_help_syntax_and_bad_arguments(script):
    path = ROOT / script
    assert (
        subprocess.run(["bash", "-n", str(path)], capture_output=True).returncode == 0
    )
    help_result = subprocess.run(
        ["bash", str(path), "--help"], capture_output=True, text=True
    )
    assert help_result.returncode == 0 and "Usage:" in help_result.stdout
    invalid = subprocess.run(
        ["bash", str(path), "--invalid"], capture_output=True, text=True
    )
    assert invalid.returncode == 1 and "[FAIL]" in invalid.stderr


def test_request_is_read_only_local_and_does_not_follow_redirects(monkeypatch):
    from unittest.mock import Mock

    connection = Mock()
    response = connection.getresponse.return_value
    response.status = 302
    response.read.return_value = b"{}"
    factory = Mock(return_value=connection)
    monkeypatch.setattr(checker, "HTTPConnection", factory)
    assert checker.request("/metrics", SecretStr("dummy-reader")) == (302, {})
    factory.assert_called_once_with("127.0.0.1", 8000, timeout=3)
    connection.request.assert_called_once_with(
        "GET", "/api/v1/metrics", headers={"Authorization": "Bearer dummy-reader"}
    )
    connection.close.assert_called_once()


@pytest.mark.parametrize("ready", [True, False])
def test_startup_wait_is_bounded(monkeypatch, ready):
    ticks = iter(range(0, 100, 5))
    monkeypatch.setattr(checker.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(checker.time, "sleep", lambda _: None)

    def request(*args):
        if ready:
            return 401, {}
        raise ConnectionRefusedError

    monkeypatch.setattr(checker, "request", request)
    if ready:
        checker.wait_for_api()
    else:
        with pytest.raises(RuntimeError):
            checker.wait_for_api()
