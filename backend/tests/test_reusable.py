"""Direct tests for the input rules shared by multiple endpoints."""

import asyncio
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException, Request
from pydantic import TypeAdapter, ValidationError

from app.reusable import (
    EventTimestamp,
    parse_server_id,
    reject_null_characters,
    validate_json_write,
    validate_list_request,
    validate_read_request,
)


def make_request(query="", body=b"", content_type=None):
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    headers = [(b"content-type", content_type.encode())] if content_type else []
    return Request(
        {"type": "http", "query_string": query.encode(), "headers": headers}, receive
    )


def test_read_accepts_a_named_parameter():
    request = make_request("server_id=1")
    asyncio.run(validate_read_request(request, "server_id"))
    assert parse_server_id(request, "1") == 1


@pytest.mark.parametrize(
    "query, value",
    [
        ("server_id=1&server_id=2", "2"),
        ("server_id=-1", "-1"),
        ("server_id=0", "0"),
        ("server_id=x", "x"),
    ],
)
def test_invalid_server_id(query, value):
    with pytest.raises(HTTPException) as error:
        parse_server_id(make_request(query), value)
    assert error.value.status_code == 400


@pytest.mark.parametrize("query, body", [("extra=1", b""), ("", b"{}")])
def test_read_rejects_unexpected_input(query, body):
    with pytest.raises(HTTPException) as error:
        asyncio.run(validate_read_request(make_request(query, body)))
    assert error.value.status_code == 422


def test_list_filters_may_each_appear_once():
    asyncio.run(
        validate_list_request(make_request("limit=1&offset=0"), "limit", "offset")
    )
    with pytest.raises(HTTPException) as error:
        asyncio.run(validate_list_request(make_request("limit=1&limit=2"), "limit"))
    assert error.value.status_code == 422


def test_json_write_returns_middleware_receipt_time():
    request = make_request(content_type="Application/JSON; charset=utf-8")
    request.state.received_at = datetime(2026, 1, 1, tzinfo=UTC)
    assert asyncio.run(validate_json_write(request)) == request.state.received_at


@pytest.mark.parametrize(
    "query, content_type, status",
    [
        ("", None, 415),
        ("", "text/plain", 415),
        ("extra=1", "application/json", 422),
    ],
)
def test_json_write_rejects_unsupported_inputs(query, content_type, status):
    with pytest.raises(HTTPException) as error:
        asyncio.run(validate_json_write(make_request(query, content_type=content_type)))
    assert error.value.status_code == status


def test_event_time_normalizes_an_offset_to_utc():
    value = TypeAdapter(EventTimestamp).validate_python("2026-01-01T02:00:00+02:00")
    assert value.isoformat() == "2026-01-01T00:00:00+00:00"


@pytest.mark.parametrize("value", [0, True, "2026-01-01T12:00:00"])
def test_event_time_rejects_numeric_or_naive_values(value):
    with pytest.raises(ValidationError):
        TypeAdapter(EventTimestamp).validate_python(value)


def test_postgresql_text_validation():
    assert reject_null_characters("Disk is full") == "Disk is full"
    with pytest.raises(ValueError, match="null characters"):
        reject_null_characters("Disk\x00full")
