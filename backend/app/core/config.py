"""Validate non-secret runtime settings before the application starts."""

from typing import Literal

from pydantic import Field, ValidationError
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


def load_settings() -> Settings:
    """Fail startup with a useful message without revealing supplied values."""
    try:
        return Settings()
    except ValidationError:
        # Do not chain Pydantic errors: future configuration may contain secrets.
        raise RuntimeError(
            "Invalid ServerWatch configuration. Check SERVERWATCH_APP_NAME "
            "and SERVERWATCH_ENVIRONMENT against .env.example."
        ) from None
