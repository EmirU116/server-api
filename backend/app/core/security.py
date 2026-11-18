"""Separate read-only dashboard and metric collector bearer credentials."""

import secrets
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import SecretStr

from app.core.config import Settings

bearer = HTTPBearer(auto_error=False)


def load_reader_token(settings: Settings) -> SecretStr | None:
    """Prefer a mounted secret file; use environment configuration locally."""
    return load_token(settings.reader_token, settings.reader_token_file, "Reader")


def load_token(
    token: SecretStr | None, path: Path | None, role: str
) -> SecretStr | None:
    """Validate either role's configured secret without exposing its contents."""
    if path is not None:
        try:
            token = SecretStr(path.read_text().strip())
        except (OSError, UnicodeError):
            raise RuntimeError(
                f"Cannot read configured {role.lower()} token file."
            ) from None

    if token is not None:
        value = token.get_secret_value()
        if not value or any(character.isspace() for character in value):
            raise RuntimeError(f"{role} token must be nonblank without whitespace.")
    return token


def require_reader(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> None:
    """Reject unauthenticated requests and fail closed without configuration."""
    require_role(request, credentials, "reader")


def require_collector(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> None:
    """Only the collector credential may submit measurements."""
    require_role(request, credentials, "collector")


def require_role(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    role: str,
) -> None:
    if credentials is None:
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Bearer"})

    expected = getattr(request.app.state, f"{role}_token")
    other_role = "collector" if role == "reader" else "reader"
    other = getattr(request.app.state, f"{other_role}_token")
    supplied = credentials.credentials.encode()
    if other is not None and secrets.compare_digest(
        supplied, other.get_secret_value().encode()
    ):
        raise HTTPException(status_code=403)
    if expected is None:
        raise HTTPException(status_code=503)

    if not secrets.compare_digest(supplied, expected.get_secret_value().encode()):
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Bearer"})
