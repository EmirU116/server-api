"""Configuration tests use dummy values and never read real local secrets."""

import traceback

import pytest

from app.core.config import load_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def clear_settings_environment(monkeypatch):
    monkeypatch.delenv("SERVERWATCH_APP_NAME", raising=False)
    monkeypatch.delenv("SERVERWATCH_ENVIRONMENT", raising=False)


def test_defaults_support_local_startup_without_credentials():
    settings = load_settings()

    assert settings.app_name == "ServerWatch"
    assert settings.environment == "development"


def test_environment_overrides(monkeypatch):
    monkeypatch.setenv("SERVERWATCH_APP_NAME", "My monitoring API")
    monkeypatch.setenv("SERVERWATCH_ENVIRONMENT", "production")

    settings = load_settings()

    assert settings.app_name == "My monitoring API"
    assert settings.environment == "production"


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SERVERWATCH_APP_NAME", "   "),
        ("SERVERWATCH_APP_NAME", "x" * 101),
        ("SERVERWATCH_ENVIRONMENT", "dummy-sensitive-invalid-value"),
    ],
)
def test_invalid_configuration_prevents_startup_without_echoing_values(
    monkeypatch, name, value
):
    monkeypatch.setenv(name, value)

    with pytest.raises(RuntimeError, match="Invalid ServerWatch configuration") as exc:
        create_app()

    assert value not in str(exc.value)
    # Traceback indentation contains spaces; check actual values separately.
    rendered = "".join(traceback.format_exception(exc.value))
    assert "input_value=" not in rendered
    if value.strip():
        assert value not in rendered
