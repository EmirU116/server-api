"""Test measurements and the five-second loop without real HTTP or secrets."""

import json
import os
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from scripts.monitoring import collect_local


def test_sample_uses_measured_host_values(monkeypatch):
    cpu = Mock(return_value=31.5)
    disk = Mock(return_value=SimpleNamespace(percent=55.0))
    monkeypatch.setattr(collect_local.psutil, "cpu_percent", cpu)
    monkeypatch.setattr(
        collect_local.psutil, "virtual_memory", lambda: SimpleNamespace(percent=45.0)
    )
    monkeypatch.setattr(collect_local.psutil, "disk_usage", disk)
    monkeypatch.setattr(collect_local.psutil, "boot_time", lambda: 1000)
    monkeypatch.setattr(collect_local.time, "time", lambda: 1012.9)

    sample = collect_local.collect_sample()

    assert sample["cpu_percent"] == 31.5
    assert sample["memory_percent"] == 45.0
    assert sample["disk_percent"] == 55.0
    assert sample["uptime_seconds"] == 12
    assert (
        datetime.fromisoformat(sample["collected_at"]).utcoffset().total_seconds() == 0
    )
    cpu.assert_called_once_with(interval=0.1)
    disk.assert_called_once_with(Path.home().anchor)


@pytest.mark.parametrize("failed", [False, True])
def test_post_is_local_authenticated_and_always_closes(monkeypatch, failed):
    connection = Mock()
    connection.getresponse.return_value.status = 201
    if failed:
        connection.request.side_effect = OSError("dummy-private-error")
    factory = Mock(return_value=connection)
    monkeypatch.setattr(collect_local, "HTTPConnection", factory)
    if failed:
        with pytest.raises(OSError):
            collect_local.post_sample({"cpu_percent": 1.2}, "dummy-collector")
    else:
        assert collect_local.post_sample({"cpu_percent": 1.2}, "dummy-collector") == 201
    factory.assert_called_once_with("127.0.0.1", 8000, timeout=3)
    arguments = connection.request.call_args
    assert arguments.args == ("POST", "/api/v1/metrics")
    assert json.loads(arguments.kwargs["body"]) == {"cpu_percent": 1.2}
    assert arguments.kwargs["headers"]["Authorization"] == "Bearer dummy-collector"
    connection.close.assert_called_once()


def test_loop_sleeps_five_seconds_and_recovers_without_leaking(monkeypatch, capsys):
    monkeypatch.setattr(collect_local, "collect_sample", lambda: {"cpu_percent": 1.2})
    post = Mock(side_effect=[201, OSError("dummy-private-error"), 503])
    sleep = Mock(side_effect=[None, None, KeyboardInterrupt])
    monkeypatch.setattr(collect_local, "post_sample", post)
    monkeypatch.setattr(collect_local.time, "sleep", sleep)

    with pytest.raises(KeyboardInterrupt):
        collect_local.run_collector("dummy-private-token")

    assert post.call_count == sleep.call_count == 3
    assert all(call.args == (5,) for call in sleep.call_args_list)
    output = capsys.readouterr().out
    assert "PASS: Local measurement recorded" in output
    assert "HTTP 503" in output
    assert "retrying" in output
    assert "dummy-private" not in output


def test_token_uses_private_file_precedence(tmp_path):
    token_file = tmp_path / "fake-token"
    token_file.write_text("dummy-file-collector\n")
    env_file = tmp_path / "fake.env"
    env_file.write_text(
        "SERVERWATCH_COLLECTOR_TOKEN=dummy-environment-collector\n"
        f'SERVERWATCH_COLLECTOR_TOKEN_FILE="{token_file.as_posix()}"\n'
    )
    with patch.dict(os.environ, {}, clear=True):
        assert collect_local.load_collector_token(env_file) == "dummy-file-collector"


def test_missing_collector_token_fails_before_loop(tmp_path):
    env_file = tmp_path / "fake.env"
    env_file.write_text("SERVERWATCH_APP_NAME=Tests\n")
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match="Configure a collector token"):
            collect_local.load_collector_token(env_file)
