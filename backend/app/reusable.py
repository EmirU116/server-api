"""Shared input rules for the ServerWatch API routers and payload schemas."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import HTTPException, Request
from pydantic import AfterValidator, AwareDatetime, BeforeValidator


def parse_server_id(request: Request, server_id: str) -> int:
    """Reject ambiguous, non-integer, zero, and negative IDs with 400."""
    if len(request.query_params.getlist("server_id")) != 1:
        raise HTTPException(status_code=400)

    try:
        value = int(server_id)
    except ValueError:
        raise HTTPException(status_code=400) from None

    if value < 1:
        raise HTTPException(status_code=400)

    return value


async def validate_read_request(request: Request, *allowed_parameters: str) -> None:
    """Allow only the named query parameters and an empty body.

    Use for server lookups and incident detail operations. Each route still
    controls how its values are parsed, including the 400 for repeated IDs.
    """
    for name in request.query_params:
        if name not in allowed_parameters:
            raise HTTPException(status_code=422)
    if await request.body():
        raise HTTPException(status_code=422)


async def validate_list_request(request: Request, *filters: str) -> None:
    """List endpoints accept one value per filter to keep pagination unambiguous."""
    await validate_read_request(request, *filters)
    for name in request.query_params:
        if len(request.query_params.getlist(name)) > 1:
            raise HTTPException(status_code=422)


async def validate_json_write(request: Request) -> datetime:
    """Require JSON and no query parameters on metric and incident writes.

    Return middleware receipt time so services can validate event timestamps
    against the same instant even when a request takes time to process.
    """
    if request.query_params:
        raise HTTPException(status_code=422)
    media_type = request.headers.get("content-type", "").partition(";")[0]
    if media_type.strip().lower() != "application/json":
        raise HTTPException(status_code=415)
    return request.state.received_at


def require_datetime_input(value: object) -> str | datetime:
    """Accept text or Python datetimes for event times before Pydantic coercion."""
    if not isinstance(value, (str, datetime)):
        raise ValueError("Use a timezone-aware datetime.")
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
        raise ValueError("Text cannot contain null characters.")
    return value
