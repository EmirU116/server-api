"""Normalize framework errors to the documented API response envelope."""

import logging
from collections.abc import Awaitable, Callable
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException

logger = logging.getLogger(__name__)

HTTP_ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    415: "unsupported_media_type",
    422: "validation_error",
    500: "internal_error",
    503: "service_unavailable",
}


def error_response(
    status_code: int,
    code: str,
    message: str,
    *,
    details: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build one stable response shape for framework and future domain errors."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details if details is not None else [],
            }
        },
        headers=headers,
    )


async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Keep protocol headers while withholding arbitrary exception details."""
    try:
        message = HTTPStatus(exc.status_code).phrase
    except ValueError:
        message = "Request failed."

    return error_response(
        exc.status_code,
        HTTP_ERROR_CODES.get(exc.status_code, "http_error"),
        message,
        headers=exc.headers,
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Separate malformed JSON from valid JSON that fails input validation.

    Never return Pydantic's input, context, or custom validator message: these
    can contain submitted credentials. Field locations still help callers find
    invalid input without echoing its value.
    """
    errors = exc.errors()
    if any(error["type"] == "json_invalid" for error in errors):
        return error_response(400, "bad_request", "Malformed JSON.")

    details = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": "Invalid or missing value.",
        }
        for error in errors
    ]
    return error_response(
        422,
        "validation_error",
        "Request validation failed.",
        details=details,
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a generic failure and log only a safe exception category.

    Raw exception strings, request bodies, URLs, and headers may contain secrets.
    Handle route failures before they reach the ASGI server's traceback logger.
    """
    logger.error("Unhandled application error (%s).", type(exc).__name__)
    return error_response(500, "internal_error", "An unexpected error occurred.")


async def unexpected_error_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Contain unexpected failures before a response begins.

    Starlette's generic exception handler re-raises errors after responding,
    which lets Uvicorn log raw exception text. Catch ordinary route failures
    here instead. Future streaming responses and background jobs need their
    own failure handling because their work can outlive the response headers.
    """
    try:
        return await call_next(request)
    except Exception as exc:
        return await unexpected_error_handler(request, exc)


def register_error_handlers(app: FastAPI) -> None:
    """Apply the same error contract to routing and request validation."""
    app.add_exception_handler(HTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.middleware("http")(unexpected_error_middleware)
