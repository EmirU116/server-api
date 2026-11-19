"""Normalize framework errors to the documented API response envelope."""

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi import HTTPException as FastAPIHTTPException
from fastapi.exceptions import RequestValidationError, ResponseValidationError
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


FIELD_MESSAGES = {
    "missing": "This field is required.",
    "int_type": "Use a whole number.",
    "int_parsing": "Use a whole number.",
    "int_parsing_size": "The number is too large to parse as an integer.",
    "int_from_float": "Use a whole number.",
    "float_type": "Use a number.",
    "float_parsing": "Use a number.",
    "finite_number": "Use a finite number.",
    "string_type": "Use text.",
    "timezone_aware": "Include a timezone offset or Z.",
    "datetime_parsing": "Use an ISO 8601 timestamp with a timezone.",
    "datetime_from_date_parsing": "Use an ISO 8601 timestamp with a timezone.",
    "datetime_type": "Use an ISO 8601 timestamp with a timezone.",
    "uuid_parsing": "Use a valid UUID.",
    "model_attributes_type": "Supply a JSON object.",
    "extra_forbidden": "Remove the unrecognized field.",
}


# Framework exceptions can carry untrusted text. Describe known conditions here.
HTTP_REASONS = {
    400: "The API could not parse the request body.",
    401: "This endpoint requires valid authentication.",
    403: "The caller lacks permission for this operation.",
    404: "No API route matches this request path.",
    405: "This route does not support the requested HTTP method.",
    409: "The request conflicts with an existing record.",
    415: "The request body has an unsupported media type.",
    422: "The request does not meet this endpoint's input requirements.",
    500: "An internal server failure interrupted request processing.",
    503: "A service required to complete this request is unavailable.",
}


class PublicHTTPError(FastAPIHTTPException):
    """An intentional client-facing explanation. Use only application-owned text."""


class PublicInputError(ValueError):
    """A schema rule with a message safe to include in validation details."""


def validation_detail(error: dict) -> dict[str, str]:
    """Describe a field rule without returning submitted values or arbitrary errors."""
    kind = error["type"]
    location = error["loc"]
    message = FIELD_MESSAGES.get(kind, "The value is invalid.")
    if kind == "extra_forbidden":
        # The unknown key itself is caller-controlled. Show its parent only.
        location = location[:-1]
    elif kind in {
        "greater_than_equal",
        "less_than_equal",
        "literal_error",
        "string_too_short",
        "string_too_long",
    }:
        # These built-in messages describe schema bounds and choices only.
        message = error["msg"]
    elif kind == "value_error":
        cause = error.get("ctx", {}).get("error")
        if isinstance(cause, PublicInputError):
            message = str(cause)
    return {"field": ".".join(str(part) for part in location), "message": message}


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
    message = HTTP_REASONS.get(exc.status_code, "The server rejected this request.")

    if isinstance(exc, PublicHTTPError):
        message = exc.detail

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

    Report known field rules with safe public messages. Submitted values and
    arbitrary exception text can contain credentials.
    """
    errors = exc.errors()
    if any(error["type"] == "json_invalid" for error in errors):
        return error_response(
            400, "bad_request", "The request body contains invalid JSON syntax."
        )

    return error_response(
        422,
        "validation_error",
        "Request validation failed.",
        details=[validation_detail(error) for error in errors],
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a generic failure and log only a safe exception category.

    Raw exception strings, request bodies, URLs, and headers may contain secrets.
    Handle route failures before they reach the ASGI server's traceback logger.
    """
    logger.error("Unhandled application error (%s).", type(exc).__name__)
    message = HTTP_REASONS[500]
    if isinstance(exc, ResponseValidationError):
        message = "The server response did not match the endpoint schema."
    return error_response(500, "internal_error", message)


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
        # Metric timestamps are compared to receipt time, before body parsing
        # or database work can make a future-dated sample appear valid.
        request.state.received_at = datetime.now(UTC)
        return await call_next(request)
    except Exception as exc:
        return await unexpected_error_handler(request, exc)


def register_error_handlers(app: FastAPI) -> None:
    """Apply the same error contract to routing and request validation."""
    app.add_exception_handler(HTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.middleware("http")(unexpected_error_middleware)
