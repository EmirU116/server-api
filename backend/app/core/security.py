"""Reader bearer authentication; no user accounts or write roles yet."""

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import SecretStr

from app.core.config import Settings

bearer = HTTPBearer(auto_error=False)


def load_reader_token(settings: Settings) -> SecretStr | None:
    """Prefer a mounted secret file; use environment configuration locally."""
    token = settings.reader_token
    if settings.reader_token_file is not None:
        try:
            token = SecretStr(settings.reader_token_file.read_text().strip())
        except (OSError, UnicodeError):
            raise RuntimeError("Cannot read configured reader token file.") from None

    if token is not None:
        value = token.get_secret_value()
        if not value or any(character.isspace() for character in value):
            raise RuntimeError("Reader token must be nonblank without whitespace.")
    return token


def require_reader(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> None:
    """Reject unauthenticated requests and fail closed without configuration."""
    if credentials is None:
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Bearer"})

    expected = request.app.state.reader_token
    if expected is None:
        raise HTTPException(status_code=503)

    if not secrets.compare_digest(
        credentials.credentials.encode(), expected.get_secret_value().encode()
    ):
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Bearer"})
