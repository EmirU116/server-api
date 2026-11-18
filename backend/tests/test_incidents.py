"""Incident HTTP contracts use injected services and dummy credentials."""

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app
from app.schemas.incident import IncidentPage, IncidentRecord
from app.services.incidents import (
    FutureIncident,
    IncidentNotFound,
    IncidentsUnavailable,
)

READER = {"Authorization": "Bearer dummy-reader"}
ADMIN = {"Authorization": "Bearer dummy-admin"}
COLLECTOR = {"Authorization": "Bearer dummy-collector"}
DATA = {
    "title": "Disk full",
    "description": "Root filesystem needs attention",
    "severity": "warning",
    "occurred_at": "2026-01-01T12:00:00Z",
}
ID = str(uuid4())


@pytest.fixture
def incidents(app):
    app.state.reader_token = SecretStr("dummy-reader")
    app.state.collector_token = SecretStr("dummy-collector")
    app.state.admin_token = SecretStr("dummy-admin")
    service = Mock()
    record = IncidentRecord(
        id=ID,
        **DATA,
        status="open",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        resolved_at=None,
    )
    service.create.return_value = record
    service.get.return_value = record
    service.update.return_value = record
    service.list.return_value = IncidentPage(items=[], total=0, limit=50, offset=0)
    app.state.incidents_service = service
    return service


def test_create_and_read_contract(client, incidents):
    created = client.post("/api/v1/incidents", json=DATA, headers=ADMIN)
    assert created.status_code == 201
    assert created.json()["status"] == "open"
    assert created.json()["resolved_at"] is None
    assert created.headers["location"] == f"/api/v1/incidents/{ID}"
    assert created.headers["cache-control"] == "no-store"
    assert client.get(f"/api/v1/incidents/{ID}", headers=READER).status_code == 200
    page = client.get("/api/v1/incidents", headers=READER)
    assert page.status_code == 200
    assert page.json() == {"items": [], "total": 0, "limit": 50, "offset": 0}


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"title": None},
        {"status": None},
        {"title": "  "},
        {"title": "a" * 201},
        {"description": "a" * 5001},
        {"title": 123},
        {"description": False},
        {"severity": "bad"},
        {"status": "closed"},
        {"occurred_at": DATA["occurred_at"]},
        {"resolved_at": None},
        {"id": ID},
        {"title": "valid", "status": "invalid"},
    ],
)
def test_invalid_patch_never_writes(client, incidents, changes):
    response = client.patch(f"/api/v1/incidents/{ID}", json=changes, headers=ADMIN)
    assert response.status_code == 422
    incidents.update.assert_not_called()


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", " "),
        ("description", "\n"),
        ("title", "a" * 201),
        ("description", "a" * 5001),
        ("title", 123),
        ("severity", "urgent"),
        ("occurred_at", "2026-01-01T00:00:00"),
        ("occurred_at", "bad"),
        ("occurred_at", 123),
        ("occurred_at", True),
        ("occurred_at", None),
        ("status", "open"),
        ("id", ID),
        ("server_id", 1),
    ],
)
def test_invalid_create_never_writes(client, incidents, field, value):
    response = client.post(
        "/api/v1/incidents", json={**DATA, field: value}, headers=ADMIN
    )
    assert response.status_code == 422
    incidents.create.assert_not_called()


@pytest.mark.parametrize("field", DATA)
def test_missing_create_field(client, incidents, field):
    data = DATA.copy()
    del data[field]
    assert client.post("/api/v1/incidents", json=data, headers=ADMIN).status_code == 422
    incidents.create.assert_not_called()


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("get", "", None),
        ("get", f"/{ID}", None),
        ("post", "", DATA),
        ("patch", f"/{ID}", {"status": "resolved"}),
        ("delete", f"/{ID}", None),
    ],
)
@pytest.mark.parametrize("role", ["missing", "invalid", "wrong"])
def test_access_control(client, incidents, method, path, body, role):
    headers = {} if role == "missing" else {"Authorization": "Bearer invalid"}
    if role == "wrong":
        headers = ADMIN if method == "get" else READER
    response = client.request(
        method, f"/api/v1/incidents{path}", json=body, headers=headers
    )
    assert response.status_code == (403 if role == "wrong" else 401)
    if role != "wrong":
        assert response.headers["www-authenticate"] == "Bearer"
    for operation in ("create", "get", "list", "update", "delete"):
        getattr(incidents, operation).assert_not_called()


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_malformed_uuid(client, incidents, method):
    response = client.request(
        method,
        "/api/v1/incidents/invalid-id",
        json={"status": "resolved"} if method == "patch" else None,
        headers=READER if method == "get" else ADMIN,
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=101",
        "offset=-1",
        "offset=9223372036854775808",
        "limit=abc",
        "limit=1&limit=2",
        "status=bad",
        "severity=bad",
        "status=open&status=resolved",
        "unknown=1",
        "server_id=1",
    ],
)
def test_invalid_list_query(client, incidents, query):
    assert client.get(f"/api/v1/incidents?{query}", headers=READER).status_code == 422
    incidents.list.assert_not_called()


def test_valid_filters_and_partial_update(client, incidents):
    assert (
        client.get(
            "/api/v1/incidents?status=open&severity=warning&limit=2&offset=1",
            headers=READER,
        ).status_code
        == 200
    )
    incidents.list.assert_called_once_with(2, 1, "open", "warning")
    assert (
        client.patch(
            f"/api/v1/incidents/{ID}",
            json={"title": "  New title  "},
            headers=ADMIN,
        ).status_code
        == 200
    )
    changes = incidents.update.call_args.args[1]
    assert changes.model_dump(exclude_unset=True) == {"title": "New title"}


@pytest.mark.parametrize(
    "method,path,operation",
    [
        ("get", f"/{ID}", "get"),
        ("patch", f"/{ID}", "update"),
        ("delete", f"/{ID}", "delete"),
        ("post", "", "create"),
        ("get", "", "list"),
    ],
)
@pytest.mark.parametrize(
    "error,expected",
    [
        (IncidentsUnavailable(), 503),
        (RuntimeError("dummy-private-error"), 500),
    ],
)
def test_failures_are_sanitized(
    client, incidents, method, path, operation, error, expected, caplog
):
    getattr(incidents, operation).side_effect = error
    response = client.request(
        method,
        f"/api/v1/incidents{path}",
        json=DATA
        if method == "post"
        else {"status": "resolved"}
        if method == "patch"
        else None,
        headers=READER if method == "get" else ADMIN,
    )
    assert response.status_code == expected
    assert "dummy-private-error" not in response.text + caplog.text


@pytest.mark.parametrize(
    "method,operation", [("get", "get"), ("patch", "update"), ("delete", "delete")]
)
def test_missing_record(client, incidents, method, operation):
    getattr(incidents, operation).side_effect = IncidentNotFound
    response = client.request(
        method,
        f"/api/v1/incidents/{ID}",
        headers=READER if method == "get" else ADMIN,
        json={"status": "open"} if method == "patch" else None,
    )
    assert response.status_code == 404


def test_delete_returns_empty_204(client, incidents):
    response = client.delete(f"/api/v1/incidents/{ID}", headers=ADMIN)
    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["cache-control"] == "no-store"


def test_future_time_and_unconfigured_storage(client, incidents, app):
    incidents.create.side_effect = FutureIncident
    assert client.post("/api/v1/incidents", json=DATA, headers=ADMIN).status_code == 422
    from app.services.incidents import IncidentsService

    app.state.incidents_service = IncidentsService(None, 1)
    assert client.get("/api/v1/incidents", headers=READER).status_code == 503
    assert client.post("/api/v1/incidents", json=DATA, headers=ADMIN).status_code == 503


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("post", "", DATA),
        ("patch", f"/{ID}", {"status": "open"}),
    ],
)
def test_json_and_query_validation(client, incidents, method, path, body):
    url = f"/api/v1/incidents{path}"
    assert (
        client.request(method, url + "?extra=1", json=body, headers=ADMIN).status_code
        == 422
    )
    assert (
        client.request(
            method, url, content="{}", headers={**ADMIN, "Content-Type": "text/plain"}
        ).status_code
        == 415
    )
    assert (
        client.request(
            method,
            url,
            content="{",
            headers={**ADMIN, "Content-Type": "application/json"},
        ).status_code
        == 400
    )
    getattr(incidents, "create" if method == "post" else "update").assert_not_called()


@pytest.mark.parametrize(
    "method,path", [("get", ""), ("get", f"/{ID}"), ("delete", f"/{ID}")]
)
def test_read_delete_reject_unsupported_input(client, incidents, method, path):
    headers = READER if method == "get" else ADMIN
    url = f"/api/v1/incidents{path}"
    assert client.request(method, url, content="{}", headers=headers).status_code == 422
    assert client.request(method, url + "?extra=1", headers=headers).status_code == 422


def test_admin_configuration_file_and_role_separation(tmp_path):
    path = tmp_path / "dummy-admin-file"
    path.write_text("dummy-file-admin\n")
    app = create_app(
        Settings(admin_token=SecretStr("dummy-env"), admin_token_file=path)
    )
    assert app.state.admin_token.get_secret_value() == "dummy-file-admin"
    assert "dummy-env" not in repr(app.state.settings)
    with pytest.raises(RuntimeError, match="Cannot read configured admin"):
        create_app(Settings(admin_token_file=tmp_path / "absent"))
    with pytest.raises(RuntimeError, match="Admin token must be nonblank"):
        create_app(Settings(admin_token=SecretStr("dummy token")))
    for role in ("reader_token", "collector_token"):
        with pytest.raises(RuntimeError, match="must be different"):
            create_app(
                Settings(admin_token=SecretStr("dummy"), **{role: SecretStr("dummy")})
            )


def test_admin_not_configured_fails_closed(client):
    assert client.post("/api/v1/incidents", json=DATA, headers=ADMIN).status_code == 503


@pytest.mark.parametrize(
    "method,path", [("put", ""), ("patch", ""), ("put", f"/{ID}"), ("post", f"/{ID}")]
)
def test_unsupported_methods(client, method, path):
    assert client.request(method, f"/api/v1/incidents{path}").status_code == 405


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("get", "", None),
        ("get", f"/{ID}", None),
        ("post", "", DATA),
        ("patch", f"/{ID}", {"status": "open"}),
        ("delete", f"/{ID}", None),
    ],
)
def test_collector_cannot_access_incidents(client, incidents, method, path, body):
    assert (
        client.request(
            method,
            f"/api/v1/incidents{path}",
            json=body,
            headers=COLLECTOR,
        ).status_code
        == 403
    )


def test_admin_does_not_gain_metric_collector_or_reader_permissions(client, incidents):
    assert client.get("/api/v1/metrics", headers=ADMIN).status_code == 403
    assert client.post("/api/v1/metrics", json={}, headers=ADMIN).status_code == 403


def test_create_trims_text_and_normalizes_timezone(client, incidents):
    data = {
        **DATA,
        "title": "  Disk full  ",
        "description": "  Check disk  ",
        "occurred_at": "2026-01-01T13:00:00+01:00",
    }
    assert client.post("/api/v1/incidents", json=data, headers=ADMIN).status_code == 201
    received = incidents.create.call_args.args[0]
    assert received.title == "Disk full"
    assert received.description == "Check disk"
    assert received.occurred_at == datetime(2026, 1, 1, 12, tzinfo=UTC)


@pytest.mark.parametrize("method", ["post", "patch"])
@pytest.mark.parametrize("field", ["title", "description"])
def test_database_incompatible_text_is_a_client_error(client, incidents, method, field):
    body = (
        {**DATA, field: "bad\x00text"} if method == "post" else {field: "bad\x00text"}
    )
    path = "/api/v1/incidents" if method == "post" else f"/api/v1/incidents/{ID}"
    assert client.request(method, path, json=body, headers=ADMIN).status_code == 422
    incidents.create.assert_not_called()
    incidents.update.assert_not_called()
