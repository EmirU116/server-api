"""Exercise shared handlers through test-only routes, not production endpoints."""

import pytest
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class SampleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cpu_percent: float = Field(ge=0, le=100, strict=True)


def add_sample_route(app):
    @app.post("/_test/sample")
    def accept_sample(sample: SampleInput):
        return sample


def test_unknown_route_has_consistent_error_envelope(client):
    response = client.get("/api/v1/not-implemented")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "Not Found", "details": []}
    }


def test_method_not_allowed_preserves_allow_header(app, client):
    add_sample_route(app)

    response = client.get("/_test/sample")

    assert response.status_code == 405
    assert response.headers["allow"] == "POST"
    assert response.json()["error"]["code"] == "method_not_allowed"


@pytest.mark.parametrize(
    "payload, reason",
    [
        ({}, "This field is required."),
        ({"cpu_percent": -1}, "Input should be greater than or equal to 0"),
        ({"cpu_percent": 101}, "Input should be less than or equal to 100"),
        ({"cpu_percent": "dummy-secret"}, "Use a number."),
    ],
)
def test_validation_errors_are_normalized_without_submitted_values(
    app, client, payload, reason
):
    add_sample_route(app)

    response = client.post("/_test/sample", json=payload)

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "validation_error",
        "message": "Request validation failed.",
        "details": [{"field": "body.cpu_percent", "message": reason}],
    }
    assert "dummy-secret" not in response.text


def test_malformed_json_returns_400(app, client):
    add_sample_route(app)

    response = client.post(
        "/_test/sample",
        content='{"cpu_percent":',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_authentication_error_preserves_challenge_without_leaking_details(app, client):
    @app.get("/_test/protected")
    def protected():
        raise HTTPException(
            status_code=401,
            detail="dummy-sensitive-token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    response = client.get("/_test/protected")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert "dummy-sensitive-token" not in response.text


def test_unexpected_failure_is_sanitized_in_response_and_application_log(
    app, client, caplog
):
    @app.get("/_test/failure")
    def fail():
        raise RuntimeError("dummy-sensitive-connection-string")

    response = client.get("/_test/failure")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "An unexpected error occurred.",
            "details": [],
        }
    }
    assert "dummy-sensitive-connection-string" not in response.text
    assert "dummy-sensitive-connection-string" not in caplog.text
    assert "Unhandled application error (RuntimeError)." in caplog.text


@pytest.mark.parametrize("resource", ["health", "server"])
@pytest.mark.parametrize(
    "query, status, message",
    [
        ("server_id=-2", 400, "server_id must be at least 1."),
        ("server_id=0", 400, "server_id must be at least 1."),
        ("server_id=dummy-sensitive", 400, "server_id must be a whole number."),
        ("server_id=1&server_id=2", 400, "Supply server_id exactly once."),
        ("server_id=2", 404, "No server is registered with this ID."),
    ],
)
def test_server_lookup_explains_failure(app, client, resource, query, status, message):
    app.state.reader_token = SecretStr("test-reader")
    response = client.get(
        f"/api/v1/{resource}?{query}", headers={"Authorization": "Bearer test-reader"}
    )
    assert response.status_code == status
    assert response.json()["error"]["message"] == message
    assert "dummy-sensitive" not in response.text


def test_unknown_body_key_is_not_echoed(app, client):
    add_sample_route(app)
    response = client.post(
        "/_test/sample", json={"cpu_percent": 1, "dummy-sensitive": 0}
    )
    assert response.json()["error"]["details"] == [
        {"field": "body", "message": "Remove the unrecognized field."}
    ]
    assert "dummy-sensitive" not in response.text


def test_arbitrary_validator_error_stays_private(app, client):
    class PrivateModel(BaseModel):
        field: str

        @field_validator("field")
        @classmethod
        def reject_value(cls, value):
            raise ValueError(f"private: {value}")

    @app.post("/_test/private")
    def accept(value: PrivateModel):
        return value

    response = client.post("/_test/private", json={"field": "dummy-sensitive"})
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["message"] == "The value is invalid."
    assert "dummy-sensitive" not in response.text
