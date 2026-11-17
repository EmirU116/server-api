"""Shared request validation for numeric server IDs."""

from fastapi import HTTPException, Request


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
