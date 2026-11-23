"""Shared input rules for the ServerWatch API routers and payload schemas."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Request
from pydantic import AfterValidator, AwareDatetime, BeforeValidator
from sqlalchemy import Engine
from sqlalchemy.exc import (
    InterfaceError,
    OperationalError,
    ProgrammingError,
    TimeoutError,
)
from sqlalchemy.orm import Session

from app.core.errors import PublicHTTPError, PublicInputError
from app.services.errors import StorageFailure, StorageUnavailable


@contextmanager
def storage_transaction(
    engine: Engine | None,
    unavailable: type[StorageUnavailable],
    *,
    snapshot: bool = False,
) -> Iterator[Session]:
    """Commit one operation or map storage failures after rollback.

    Use a repeatable snapshot when a list reads its count and page separately.
    Resource-specific constraints and row locks belong to the caller.
    """
    if engine is None:
        raise unavailable(StorageFailure.UNCONFIGURED)
    try:
        with engine.connect() as connection:
            if snapshot:
                connection = connection.execution_options(
                    isolation_level="REPEATABLE READ"
                )
            with Session(bind=connection) as session, session.begin():
                yield session
    except (
        OperationalError,
        InterfaceError,
        ProgrammingError,
        TimeoutError,
    ) as exc:
        raise unavailable.from_database_error(exc) from None


def parse_server_id(request: Request, server_id: str) -> int:
    """Reject ambiguous, non-integer, zero, and negative IDs with 400."""
    if len(request.query_params.getlist("server_id")) != 1:
        raise PublicHTTPError(400, "Supply server_id exactly once.")

    try:
        value = int(server_id)
    except ValueError:
        raise PublicHTTPError(400, "server_id must be a whole number.") from None

    if value < 1:
        raise PublicHTTPError(400, "server_id must be at least 1.")

    return value


async def validate_read_request(request: Request, *allowed_parameters: str) -> None:
    """Allow only the named query parameters and an empty body.

    Use for server lookups and incident detail operations. Each route still
    controls how its values are parsed, including the 400 for repeated IDs.
    """
    for name in request.query_params:
        if name not in allowed_parameters:
            if allowed_parameters:
                allowed = ", ".join(allowed_parameters)
                raise PublicHTTPError(
                    422, f"Unsupported query parameter. Allowed: {allowed}."
                )
            raise PublicHTTPError(
                422, "This operation does not accept query parameters."
            )
    if await request.body():
        raise PublicHTTPError(422, "This operation does not accept a request body.")


async def validate_list_request(request: Request, *filters: str) -> None:
    """List endpoints accept one value per filter to keep pagination unambiguous."""
    await validate_read_request(request, *filters)
    for name in request.query_params:
        if len(request.query_params.getlist(name)) > 1:
            raise PublicHTTPError(422, f"Supply the {name} filter only once.")


async def validate_json_write(request: Request) -> datetime:
    """Require JSON and no query parameters on metric and incident writes.

    Return middleware receipt time so services can validate event timestamps
    against the same instant even when a request takes time to process.
    """
    if request.query_params:
        raise PublicHTTPError(
            422, "This write operation does not accept query parameters."
        )
    media_type = request.headers.get("content-type", "").partition(";")[0]
    if media_type.strip().lower() != "application/json":
        raise PublicHTTPError(
            415,
            "A JSON body is required. Set Content-Type to application/json.",
        )
    return request.state.received_at


def require_datetime_input(value: object) -> str | datetime:
    """Accept text or Python datetimes for event times before Pydantic coercion."""
    if not isinstance(value, (str, datetime)):
        raise PublicInputError("Use an ISO 8601 timestamp with a timezone.")
    return value


def as_utc(value: datetime) -> datetime:
    """Normalize a validated aware time for consistent storage and responses."""
    return value.astimezone(UTC)


# Client-supplied event times have stricter input rules than database timestamps.
UtcDatetime = Annotated[AwareDatetime, AfterValidator(as_utc)]
EventTimestamp = Annotated[UtcDatetime, BeforeValidator(require_datetime_input)]


def reject_null_characters(value: str) -> str:
    """Reject embedded nulls on text fields destined for PostgreSQL."""
    if "\x00" in value:
        raise PublicInputError("Remove null characters from the text.")
    return value
