"""HTTP validation and role tests do not depend on PostgreSQL."""

import json
from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app
from app.schemas.metric import MetricPage, MetricRecord
from app.services.metrics import DuplicateMetric, MetricsUnavailable

SAMPLE = {
    "collected_at": "2026-01-01T12:00:00Z",
    "cpu_percent": 27.5,
    "memory_percent": 61.2,
    "disk_percent": 43.8,
    "uptime_seconds": 86400,
}
READER = {"Authorization": "Bearer dummy-reader"}
COLLECTOR = {"Authorization": "Bearer dummy-collector"}


@pytest.fixture
def metrics(app):
    app.state.reader_token = SecretStr("dummy-reader")
    app.state.collector_token = SecretStr("dummy-collector")
    service = Mock()
    service.create.return_value = MetricRecord(id=uuid4(), **SAMPLE)
    service.list.return_value = MetricPage(items=[], total=0, limit=50, offset=0)
    app.state.metrics_service = service
    return service


def test_create_returns_generated_record(client, metrics):
    response = client.post("/api/v1/metrics", json=SAMPLE, headers=COLLECTOR)
    assert response.status_code == 201
    assert response.json()["cpu_percent"] == 27.5
    assert "id" in response.json()
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("field", ["cpu_percent", "memory_percent", "disk_percent"])
@pytest.mark.parametrize("value", [-1, 101, "30", True, None])
def test_invalid_percentages_do_not_write(client, metrics, field, value):
    response = client.post(
        "/api/v1/metrics", json={**SAMPLE, field: value}, headers=COLLECTOR
    )
    assert response.status_code == 422
    metrics.create.assert_not_called()


@pytest.mark.parametrize("value", [-1, 1.5, True, "30", None, 9223372036854775808])
def test_invalid_uptime(client, metrics, value):
    response = client.post(
        "/api/v1/metrics", json={**SAMPLE, "uptime_seconds": value}, headers=COLLECTOR
    )
    assert response.status_code == 422
    metrics.create.assert_not_called()


@pytest.mark.parametrize("field", list(SAMPLE))
def test_missing_fields(client, metrics, field):
    data = SAMPLE.copy()
    del data[field]
    assert (
        client.post("/api/v1/metrics", json=data, headers=COLLECTOR).status_code == 422
    )


@pytest.mark.parametrize("value", ["bad-time", "2026-01-01T12:00:00", 123, True, None])
def test_invalid_timestamp(client, metrics, value):
    response = client.post(
        "/api/v1/metrics", json={**SAMPLE, "collected_at": value}, headers=COLLECTOR
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "method,headers,expected",
    [
        ("get", {}, 401),
        ("post", {}, 401),
        ("get", COLLECTOR, 403),
        ("post", READER, 403),
        ("get", {"Authorization": "Bearer wrong"}, 401),
        ("post", {"Authorization": "Bearer wrong"}, 401),
    ],
)
def test_roles(client, metrics, method, headers, expected):
    response = client.request(
        method,
        "/api/v1/metrics",
        json=SAMPLE if method == "post" else None,
        headers=headers,
    )
    assert response.status_code == expected
    if expected == 401:
        assert response.headers["www-authenticate"] == "Bearer"
    metrics.create.assert_not_called()
    metrics.list.assert_not_called()


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=101",
        "offset=-1",
        "limit=abc",
        "limit=1&limit=2",
        "verbose=true",
        "start=bad",
        "start=2026-01-01T12:00:00",
        "start=2026-01-02T00:00:00Z&end=2026-01-01T00:00:00Z",
    ],
)
def test_invalid_query_does_not_read(client, metrics, query):
    assert client.get(f"/api/v1/metrics?{query}", headers=READER).status_code == 422
    metrics.list.assert_not_called()


def test_get_empty_collection_and_valid_filters(client, metrics):
    response = client.get(
        "/api/v1/metrics?limit=1&offset=2&start=2026-01-01T00:00:00Z", headers=READER
    )
    assert response.status_code == 200
    metrics.list.assert_called_once_with(1, 2, datetime(2026, 1, 1, tzinfo=UTC), None)


def test_get_rejects_body(client, metrics):
    assert (
        client.request(
            "GET", "/api/v1/metrics", content="{}", headers=READER
        ).status_code
        == 422
    )


@pytest.mark.parametrize("method", ["put", "patch", "delete", "head", "options"])
def test_only_get_and_post(client, method):
    response = client.request(method, "/api/v1/metrics")
    assert response.status_code == 405


def test_content_type_malformed_json_and_unknown_input(client, metrics):
    response = client.post(
        "/api/v1/metrics",
        content="{}",
        headers={**COLLECTOR, "Content-Type": "text/plain"},
    )
    assert response.status_code == 415
    assert "application/json" in response.json()["error"]["message"]
    response = client.post(
        "/api/v1/metrics",
        content="{",
        headers={**COLLECTOR, "Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert (
        client.post(
            "/api/v1/metrics", json={**SAMPLE, "id": str(uuid4())}, headers=COLLECTOR
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/metrics?extra=1", json=SAMPLE, headers=COLLECTOR
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "error,status",
    [
        (DuplicateMetric(), 409),
        (MetricsUnavailable(), 503),
        (RuntimeError("dummy-secret"), 500),
    ],
)
def test_write_errors_sanitized(client, metrics, error, status, caplog):
    metrics.create.side_effect = error
    response = client.post("/api/v1/metrics", json=SAMPLE, headers=COLLECTOR)
    assert response.status_code == status
    reasons = {
        409: "already exists",
        503: "PostgreSQL could not complete",
        500: "internal server failure",
    }
    assert reasons[status] in response.json()["error"]["message"]
    assert "dummy-secret" not in response.text + caplog.text


def test_read_storage_failure(client, metrics):
    metrics.list.side_effect = MetricsUnavailable
    assert client.get("/api/v1/metrics", headers=READER).status_code == 503


def test_missing_database_returns_503(client, app):
    app.state.reader_token = SecretStr("dummy-reader")
    app.state.collector_token = SecretStr("dummy-collector")
    assert client.get("/api/v1/metrics", headers=READER).status_code == 503
    assert (
        client.post("/api/v1/metrics", json=SAMPLE, headers=COLLECTOR).status_code
        == 503
    )


@pytest.mark.parametrize(
    ("query", "reason"),
    [
        ("minutes=31", "minutes must be 30, 60, or 1440."),
        ("minutes=30&minutes=60", "Supply the minutes filter only once."),
    ],
)
def test_invalid_history_query_explains_failure(client, app, query, reason):
    app.state.reader_token = SecretStr("dummy-reader")
    response = client.get(f"/api/v1/metrics/history?{query}", headers=READER)
    assert response.status_code == 422
    assert response.json()["error"]["message"] == reason


def test_history_requires_reader_and_storage(client, app):
    app.state.reader_token = SecretStr("dummy-reader")
    path = "/api/v1/metrics/history"
    assert client.get(path).status_code == 401
    response = client.get(path, headers=READER)
    assert response.status_code == 503
    assert "storage has not been configured" in response.json()["error"]["message"]


def test_roles_cannot_share_same_token():
    with pytest.raises(RuntimeError, match="must be different"):
        create_app(
            Settings(
                reader_token=SecretStr("dummy"), collector_token=SecretStr("dummy")
            )
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_percentages_do_not_write(client, metrics, value):
    response = client.post(
        "/api/v1/metrics",
        content=json.dumps({**SAMPLE, "cpu_percent": value}),
        headers={**COLLECTOR, "Content-Type": "application/json"},
    )
    assert response.status_code == 422
    metrics.create.assert_not_called()


def test_collector_file_precedence_and_invalid_configuration(tmp_path):
    path = tmp_path / "fake-collector-token"
    path.write_text("dummy-file-collector\n")
    app = create_app(
        Settings(
            collector_token=SecretStr("dummy-env-collector"), collector_token_file=path
        )
    )
    assert app.state.collector_token.get_secret_value() == "dummy-file-collector"
    with pytest.raises(RuntimeError, match="Collector token must be nonblank"):
        create_app(Settings(collector_token=SecretStr("dummy token")))
    with pytest.raises(RuntimeError, match="Cannot read configured collector"):
        create_app(Settings(collector_token_file=tmp_path / "absent"))


def test_unconfigured_collector_fails_closed(client):
    assert (
        client.post("/api/v1/metrics", json=SAMPLE, headers=COLLECTOR).status_code
        == 503
    )
