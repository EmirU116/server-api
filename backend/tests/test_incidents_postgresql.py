"""Exercise incident persistence and transitions in disposable PostgreSQL only."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import delete, text
from test_incidents import ADMIN, DATA, READER

from app.models.incident import Incident
from app.schemas.incident import IncidentCreate, IncidentUpdate
from app.services.incidents import FutureIncident, IncidentNotFound, IncidentsService


@pytest.fixture
def stored_incidents(postgres_engine, app):
    with postgres_engine.begin() as connection:
        connection.execute(delete(Incident))
    service = IncidentsService(postgres_engine, 1)
    app.state.incidents_service = service
    app.state.admin_token = SecretStr("dummy-admin")
    app.state.reader_token = SecretStr("dummy-reader")
    return service


def test_full_crud_persists_and_deletion_is_final(
    client, stored_incidents, postgres_engine
):
    created = client.post("/api/v1/incidents", json=DATA, headers=ADMIN)
    assert created.status_code == 201
    record = created.json()
    incident_id = UUID(record["id"])
    assert record["created_at"] == record["updated_at"]
    postgres_engine.dispose()
    assert IncidentsService(postgres_engine, 1).get(incident_id).title == DATA["title"]
    assert client.get(created.headers["location"], headers=READER).json() == record
    changed = client.patch(
        created.headers["location"],
        json={"title": "  Investigate  ", "status": "investigating"},
        headers=ADMIN,
    )
    assert changed.status_code == 200
    assert changed.json()["title"] == "Investigate"
    assert changed.json()["description"] == DATA["description"]
    assert changed.json()["occurred_at"] == record["occurred_at"]
    assert stored_incidents.get(incident_id).status == "investigating"
    response = client.delete(created.headers["location"], headers=ADMIN)
    assert response.status_code == 204 and response.content == b""
    assert client.get(created.headers["location"], headers=READER).status_code == 404
    assert client.delete(created.headers["location"], headers=ADMIN).status_code == 404


def test_plan_can_be_saved_and_opened_later(client, stored_incidents):
    trigger = {"metric": "storage", "threshold_percent": 90, "duration_seconds": 600}
    created = client.post(
        "/api/v1/incidents",
        json={**DATA, "occurred_at": None, "trigger": trigger},
        headers=ADMIN,
    )
    assert created.status_code == 201
    path = created.headers["location"]
    assert created.json()["status"] == "planned"
    assert created.json()["occurred_at"] is None
    assert client.get(path, headers=READER).json()["trigger"] == trigger
    updated = client.patch(path, json={"title": "Practice recovery"}, headers=ADMIN)
    assert updated.status_code == 200
    assert updated.json()["occurred_at"] is None
    assert updated.json()["trigger"] == trigger
    opened = client.patch(path, json={"status": "open"}, headers=ADMIN)
    assert opened.status_code == 200
    assert opened.json()["occurred_at"] is not None
    assert client.get(path, headers=READER).json() == opened.json()
    cleared = client.patch(path, json={"trigger": None}, headers=ADMIN)
    assert cleared.status_code == 200
    assert client.get(path, headers=READER).json()["trigger"] is None


def test_resolution_preserved_and_reopening_clears_time(stored_incidents):
    now = datetime(2026, 2, 1, tzinfo=UTC)
    stored_incidents.clock = lambda: now
    record = stored_incidents.create(IncidentCreate(**DATA), now)
    now += timedelta(seconds=1)
    resolved = stored_incidents.update(record.id, IncidentUpdate(status="resolved"))
    assert resolved.resolved_at == now
    resolution_time = now
    now += timedelta(seconds=1)
    edited = stored_incidents.update(record.id, IncidentUpdate(description="Fixed"))
    assert edited.resolved_at == resolution_time
    assert edited.updated_at == now
    unchanged = stored_incidents.update(record.id, IncidentUpdate(status="resolved"))
    assert unchanged.resolved_at == resolution_time
    for status in ("open", "investigating"):
        reopened = stored_incidents.update(record.id, IncidentUpdate(status=status))
        assert reopened.resolved_at is None
        stored_incidents.update(record.id, IncidentUpdate(status="resolved"))


def test_list_filters_order_count_and_server_isolation(
    client, stored_incidents, postgres_engine
):
    now = datetime(2026, 2, 1, tzinfo=UTC)
    stored_incidents.clock = lambda: now
    records = []
    for severity in ("warning", "critical", "warning"):
        records.append(
            stored_incidents.create(
                IncidentCreate(**{**DATA, "severity": severity}), now
            )
        )
        now += timedelta(seconds=1)
    stored_incidents.update(records[0].id, IncidentUpdate(status="resolved"))
    page = client.get(
        "/api/v1/incidents?status=open&severity=warning", headers=READER
    ).json()
    assert page["total"] == 1
    assert page["items"][0]["id"] == str(records[2].id)
    page = stored_incidents.list(1, 1)
    assert page.total == 3 and page.items[0].id == records[1].id
    assert stored_incidents.list(1, 100).items == []
    other_server = IncidentsService(postgres_engine, 2)
    assert other_server.list(50, 0).total == 0
    for operation in (
        lambda: other_server.get(records[0].id),
        lambda: other_server.update(records[0].id, IncidentUpdate(status="open")),
        lambda: other_server.delete(records[0].id),
    ):
        with pytest.raises(IncidentNotFound):
            operation()
    assert stored_incidents.list(50, 0).total == 3


def test_invalid_change_and_future_create_leave_database_unchanged(
    client, stored_incidents
):
    created = client.post("/api/v1/incidents", json=DATA, headers=ADMIN)
    url = created.headers["location"]
    assert (
        client.patch(
            url, json={"title": "changed", "severity": "bad"}, headers=ADMIN
        ).status_code
        == 422
    )
    assert client.get(url, headers=READER).json() == created.json()
    future = {
        **DATA,
        "occurred_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
    }
    assert (
        client.post("/api/v1/incidents", json=future, headers=ADMIN).status_code == 422
    )
    with pytest.raises(FutureIncident):
        stored_incidents.create(IncidentCreate(**future), datetime.now(UTC))
    assert stored_incidents.list(50, 0).total == 1


def test_missing_tables_return_503_for_all_operations(
    client, app, stored_incidents, postgres_engine
):
    missing_schema = postgres_engine.execution_options(
        schema_translate_map={None: "missing_incidents"}
    )
    app.state.incidents_service = IncidentsService(missing_schema, 1)
    incident_id = uuid4()
    for method, path, body in (
        ("get", "", None),
        ("get", f"/{incident_id}", None),
        ("post", "", DATA),
        ("patch", f"/{incident_id}", {"status": "open"}),
        ("delete", f"/{incident_id}", None),
    ):
        response = client.request(
            method,
            f"/api/v1/incidents{path}",
            json=body,
            headers=READER if method == "get" else ADMIN,
        )
        assert response.status_code == 503
        assert "Check the migrations" in response.json()["error"]["message"]
        assert "missing_incidents" not in response.text


def test_failed_transaction_rolls_back_and_next_write_succeeds(stored_incidents):
    record = stored_incidents.create(IncidentCreate(**DATA), datetime.now(UTC))
    with pytest.raises(RuntimeError):
        with stored_incidents.transaction() as session:
            persisted = stored_incidents.find(session, record.id, lock=True)
            persisted.title = "Must roll back"
            session.flush()
            raise RuntimeError("simulated failure before commit")
    assert stored_incidents.get(record.id).title == DATA["title"]
    assert (
        stored_incidents.update(record.id, IncidentUpdate(title="Good edit")).title
        == "Good edit"
    )


def test_upgrade_preserves_existing_metrics_and_incidents(postgres_engine):
    from pathlib import Path

    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    # A separate schema in this disposable cluster represents an existing user's
    # metrics-only installation. No real database or downgrade is involved.
    with postgres_engine.begin() as connection:
        connection.execute(text("CREATE SCHEMA upgrade_test"))
        connection.execute(text("SET LOCAL search_path TO upgrade_test"))
        config.attributes["connection"] = connection
        command.upgrade(config, "0001_metrics")
        metric_id = uuid4()
        connection.execute(
            text("INSERT INTO metrics VALUES (:id, '1', now(), 1, 2, 3, 4)"),
            {"id": metric_id},
        )
        command.upgrade(config, "0002_incidents")
        incident_id = uuid4()
        connection.execute(
            text(
                "INSERT INTO incidents (id, server_id, title, description, "
                "severity, status, occurred_at, created_at, updated_at) "
                "VALUES (:id, '1', 'Existing', 'Keep this record', "
                "'warning', 'open', now(), now(), now())"
            ),
            {"id": incident_id},
        )
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        assert connection.scalar(text("SELECT id FROM metrics")) == metric_id
        assert connection.scalar(text("SELECT id FROM incidents")) == incident_id
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version"))
            == "0004_incident_triggers"
        )
