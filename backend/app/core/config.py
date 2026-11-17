"""Validate runtime settings and keep configured credentials hidden."""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read SERVERWATCH_* environment variables with local development defaults.

    Dotenv loading is explicit through Uvicorn's --env-file option. Tests can
    inject settings without reading a developer's local credential files.
    Database credentials become required when persistence is implemented.
    """

    model_config = SettingsConfigDict(
        env_prefix="SERVERWATCH_",
        hide_input_in_errors=True,
        str_strip_whitespace=True,
        frozen=True,
    )

    app_name: str = Field(default="ServerWatch", min_length=1, max_length=100)
    environment: Literal["development", "test", "production"] = "development"
    server_id: int = Field(default=1, ge=1)
    server_name: str = Field(default="ServerWatch server", min_length=1, max_length=200)
    reader_token: SecretStr | None = Field(default=None, repr=False)
    reader_token_file: Path | None = Field(default=None, repr=False)


def load_settings() -> Settings:
    """Fail startup with a useful message without revealing supplied values."""
    try:
        return Settings()
    except ValidationError:
        # Do not chain Pydantic errors: future configuration may contain secrets.
        raise RuntimeError(
            "Invalid ServerWatch configuration. Check SERVERWATCH_* settings "
            "against .env.example."
        ) from None
