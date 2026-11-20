"""Real persistence tests use a private temporary PostgreSQL cluster only.

No existing database or credential file is accessed. PostgreSQL server tools
must already be installed; otherwise these integration tests are skipped.
"""

from datetime import UTC, datetime, timedelta

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from pydantic import SecretStr
from sqlalchemy import delete, inspect, text
from test_metrics import COLLECTOR, READER, SAMPLE

from app.models.metric import Base, Metric
from app.schemas.metric import MetricCreate
from app.services.metrics import DuplicateMetric, FutureMetric, MetricsService


@pytest.fixture
def stored_metrics(postgres_engine, app):
    with postgres_engine.begin() as connection:
        connection.execute(delete(Metric))
    service = MetricsService(postgres_engine, 1)
    app.state.metrics_service = service
    app.state.reader_token = SecretStr("dummy-reader")
    app.state.collector_token = SecretStr("dummy-collector")
    return service


def test_post_get_duplicate_rollback_and_restart(
    client, stored_metrics, postgres_engine
):
    response = client.post("/api/v1/metrics", json=SAMPLE, headers=COLLECTOR)
    assert response.status_code == 201
    record = response.json()
    assert (
        client.post("/api/v1/metrics", json=SAMPLE, headers=COLLECTOR).status_code
        == 409
    )
    assert client.get("/api/v1/metrics", headers=READER).json()["items"] == [record]
    # New service and fresh connections still see committed records.
    postgres_engine.dispose()
    restarted = MetricsService(postgres_engine, 1)
    assert restarted.list(50, 0, None, None).total == 1
    next_sample = {**SAMPLE, "collected_at": "2026-01-01T12:01:00Z"}
    assert (
        client.post("/api/v1/metrics", json=next_sample, headers=COLLECTOR).status_code
        == 201
    )
    assert restarted.list(50, 0, None, None).total == 2


def test_order_filters_pagination_and_server_isolation(stored_metrics, postgres_engine):
    now = datetime.now(UTC)
    for minute in range(3):
        sample = MetricCreate(
            **{**SAMPLE, "collected_at": f"2026-01-01T12:0{minute}:00Z"}
        )
        stored_metrics.create(sample, now)
    page = stored_metrics.list(1, 1, None, None)
    assert page.total == 3
    assert page.items[0].collected_at == datetime(2026, 1, 1, 12, 1, tzinfo=UTC)
    bound = datetime(2026, 1, 1, 12, 1, tzinfo=UTC)
    filtered = stored_metrics.list(50, 0, bound, bound)
    assert filtered.total == 1
    assert filtered.items[0].collected_at == bound
    assert stored_metrics.list(1, 20, None, None).items == []
    assert MetricsService(postgres_engine, 2).list(50, 0, None, None).total == 0
    assert stored_metrics.list(1, 0, None, None).items[0].collected_at.minute == 2


@pytest.mark.parametrize("value", [0, 100])
def test_percentage_boundaries_and_timezone_uniqueness(stored_metrics, value):
    now = datetime.now(UTC)
    sample = MetricCreate(
        **{
            **SAMPLE,
            "cpu_percent": value,
            "memory_percent": value,
            "disk_percent": value,
            "uptime_seconds": 0,
        }
    )
    stored_metrics.create(sample, now)
    equivalent = sample.model_copy(
        update={"collected_at": datetime.fromisoformat("2026-01-01T13:00:00+01:00")}
    )
    with pytest.raises(DuplicateMetric):
        stored_metrics.create(equivalent, now)
    assert stored_metrics.list(50, 0, None, None).total == 1


def test_future_timestamp_cannot_write(client, stored_metrics):
    data = {
        **SAMPLE,
        "collected_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
    }
    assert (
        client.post("/api/v1/metrics", json=data, headers=COLLECTOR).status_code == 422
    )
    with pytest.raises(FutureMetric):
        stored_metrics.create(MetricCreate(**data), datetime.now(UTC))
    assert stored_metrics.list(50, 0, None, None).total == 0


def test_migration_matches_model(postgres_engine):
    inspector = inspect(postgres_engine)
    assert "metrics" in inspector.get_table_names()
    assert {column["name"] for column in inspector.get_columns("metrics")} == set(
        Metric.__table__.columns.keys()
    )
    with postgres_engine.connect() as connection:
        assert (
            compare_metadata(MigrationContext.configure(connection), Base.metadata)
            == []
        )
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version"))
            == "0004_incident_triggers"
        )


def test_missing_schema_returns_safe_503(client, app, stored_metrics, postgres_engine):
    missing_schema = postgres_engine.execution_options(
        schema_translate_map={None: "serverwatch_missing_schema"}
    )
    app.state.metrics_service = MetricsService(missing_schema, 1)
    read = client.get("/api/v1/metrics", headers=READER)
    write = client.post("/api/v1/metrics", json=SAMPLE, headers=COLLECTOR)
    assert read.status_code == write.status_code == 503
    for response in (read, write):
        assert "Check the migrations" in response.json()["error"]["message"]
    assert "serverwatch_missing_schema" not in read.text + write.text
