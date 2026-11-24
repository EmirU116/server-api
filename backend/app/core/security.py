"""Separate reader, collector, and incident administrator credentials."""

import secrets
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import SecretStr

from app.core.config import read_secret_file
from app.core.errors import PublicHTTPError

bearer = HTTPBearer(auto_error=False)


def load_token(
    token: SecretStr | None, path: Path | None, role: str
) -> SecretStr | None:
    """Load one role's secret, preferring a mounted file over the environment.

    The value is validated without exposing its contents in errors.
    """
    if path is not None:
        token = read_secret_file(path, f"{role.lower()} token")

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


def require_admin(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> None:
    """Only administrators may create, edit, or delete incidents."""
    require_role(request, credentials, "admin")


def require_role(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    role: str,
) -> None:
    if credentials is None:
        raise PublicHTTPError(
            401,
            "A Bearer token is required in the Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expected = getattr(request.app.state, f"{role}_token")
    supplied = credentials.credentials.encode()
    for other_role in ("reader", "collector", "admin"):
        if other_role == role:
            continue
        other = getattr(request.app.state, f"{other_role}_token")
        if other is not None and secrets.compare_digest(
            supplied, other.get_secret_value().encode()
        ):
            raise PublicHTTPError(403, f"This operation requires the {role} role.")
    if expected is None:
        raise PublicHTTPError(
            503, f"The server has no credential configured for the {role} role."
        )

    if not secrets.compare_digest(supplied, expected.get_secret_value().encode()):
        raise PublicHTTPError(
            401,
            "The supplied Bearer token was not recognized.",
            headers={"WWW-Authenticate": "Bearer"},
        )
