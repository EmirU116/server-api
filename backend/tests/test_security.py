"""Reader token tests use dummy values and temporary files only."""

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.security import load_token


def load_reader_token(settings: Settings):
    return load_token(settings.reader_token, settings.reader_token_file, "Reader")


def test_reader_token_is_optional_and_hidden():
    assert load_reader_token(Settings()) is None
    settings = Settings(reader_token=SecretStr("dummy-sensitive-token"))
    assert load_reader_token(settings).get_secret_value() == "dummy-sensitive-token"
    assert "dummy-sensitive" not in repr(settings)


def test_reader_token_file_takes_precedence(tmp_path):
    token_file = tmp_path / "dummy-token.txt"
    token_file.write_text("dummy-file-token\n")
    settings = Settings(
        reader_token=SecretStr("dummy-env-token"), reader_token_file=token_file
    )

    assert load_reader_token(settings).get_secret_value() == "dummy-file-token"


@pytest.mark.parametrize("token", ["", " ", "dummy token", "dummy\ntoken"])
def test_invalid_token_configuration_fails_safely(token):
    with pytest.raises(RuntimeError, match="Reader token must be nonblank"):
        load_reader_token(Settings(reader_token=SecretStr(token)))


def test_unreadable_file_does_not_fall_back_or_leak_path(tmp_path):
    with pytest.raises(RuntimeError) as error:
        load_reader_token(Settings(reader_token_file=tmp_path / "dummy-sensitive-path"))

    assert "dummy-sensitive" not in str(error.value)
