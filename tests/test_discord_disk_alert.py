"""Test alerts with fake measurements and a fake Discord connection."""

import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "discord_disk_alert", ROOT / "scripts/monitoring/discord_disk_alert.py"
)
alerts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(alerts)

WEBHOOK_PATH = "/api/webhooks/1234/fake-test-credential"


@pytest.mark.parametrize(
    "url",
    [
        "http://discord.com",
        "https://discord.com.evil.example",
        "https://discord.com@evil.example",
        "https://discord.com:443",
    ],
)
def test_reject_invalid_webhook_without_exposing_its_path(url):
    with pytest.raises(alerts.AlertError) as error:
        alerts.webhook_path(url + WEBHOOK_PATH)
    assert WEBHOOK_PATH not in str(error.value)
    assert alerts.webhook_path("https://discord.com" + WEBHOOK_PATH) == WEBHOOK_PATH


def test_threshold_suppresses_duplicates_and_rearms_on_recovery(tmp_path, monkeypatch):
    state = tmp_path / "state"
    usage = iter(
        [(100, 80, 20), (100, 90, 10), (100, 91, 9), (100, 89, 11), (100, 92, 8)]
    )
    transport = Mock()
    monkeypatch.setattr(alerts.shutil, "disk_usage", lambda _: next(usage))
    monkeypatch.setattr(alerts, "send_alert", transport)

    assert "below" in alerts.check_disk(90, WEBHOOK_PATH, state)
    assert not state.exists()
    assert "delivered" in alerts.check_disk(90, WEBHOOK_PATH, state)
    assert state.read_text() == "alerted"
    assert "Already alerted" in alerts.check_disk(90, WEBHOOK_PATH, state)
    assert transport.call_count == 1
    assert "below" in alerts.check_disk(90, WEBHOOK_PATH, state)
    assert state.read_text() == "clear"
    assert "delivered" in alerts.check_disk(90, WEBHOOK_PATH, state)
    assert transport.call_count == 2


def test_failed_delivery_stays_eligible_for_retry(tmp_path, monkeypatch):
    state = tmp_path / "state"
    monkeypatch.setattr(alerts.shutil, "disk_usage", lambda _: (100, 95, 5))
    transport = Mock(side_effect=[alerts.AlertError("Network unavailable"), None])
    monkeypatch.setattr(alerts, "send_alert", transport)
    with pytest.raises(alerts.AlertError, match="Network unavailable"):
        alerts.check_disk(90, WEBHOOK_PATH, state)
    assert not state.exists()
    assert "delivered" in alerts.check_disk(90, WEBHOOK_PATH, state)


@pytest.mark.parametrize("status", [200, 302, 401, 429])
def test_discord_request_redacts_credential_disables_mentions_and_checks_status(
    monkeypatch, status
):
    connection = Mock()
    connection.getresponse.return_value = SimpleNamespace(status=status)
    https = Mock(return_value=connection)
    monkeypatch.setattr(alerts.http.client, "HTTPSConnection", https)
    if status == 200:
        alerts.send_alert(WEBHOOK_PATH, "alert")
    else:
        with pytest.raises(alerts.AlertError, match=f"HTTP {status}") as error:
            alerts.send_alert(WEBHOOK_PATH, "alert")
        assert WEBHOOK_PATH not in str(error.value)
    https.assert_called_once_with("discord.com", timeout=8)
    assert connection.request.call_args.args == ("POST", f"{WEBHOOK_PATH}?wait=true")
    assert json.loads(connection.request.call_args.kwargs["body"]) == {
        "content": "alert",
        "allowed_mentions": {"parse": []},
    }
    connection.close.assert_called_once()


def test_installer_help_does_not_require_ubuntu():
    bootstrap = ROOT / "infrastructure/bootstrap/setup_discord_alerts.sh"
    result = subprocess.run(
        ["bash", str(bootstrap), "--help"],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    assert "WEBHOOK_FILE" in result.stdout
