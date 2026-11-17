"""Health contract and probe tests; no live database or EC2 calls."""

import asyncio
from datetime import UTC, datetime
from time import perf_counter

import pytest

from app.services.health import HealthService

CHECKED_AT = datetime(2026, 11, 16, 12, tzinfo=UTC)


async def up() -> bool:
    return True


async def down() -> bool:
    return False


async def failed() -> bool:
    raise RuntimeError("dummy-sensitive-connection-string")


def test_default_health_is_public_and_honest_about_missing_database(client):
    response = client.get("/api/v1/health?server_id=1")

    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
    assert response.json()["checks"] == {"server": "up", "database": "down"}
    assert (
        datetime.fromisoformat(response.json()["checked_at"])
        .utcoffset()
        .total_seconds()
        == 0
    )
    assert response.headers["cache-control"] == "no-store"
    assert "www-authenticate" not in response.headers


def test_healthy_response_uses_utc_time_and_documented_structure(app, client):
    app.state.health_service = HealthService(up, up, clock=lambda: CHECKED_AT)

    response = client.get("/api/v1/health?server_id=1")

    assert response.status_code == 200
    assert response.json() == {
        "server_id": 1,
        "status": "healthy",
        "checked_at": "2026-11-16T12:00:00Z",
        "checks": {"server": "up", "database": "up"},
    }


@pytest.mark.parametrize("server,database", [(down, up), (up, down), (down, down)])
def test_failed_checks_return_503(app, client, server, database):
    app.state.health_service = HealthService(server, database, clock=lambda: CHECKED_AT)

    response = client.get("/api/v1/health?server_id=1")

    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
    assert response.json()["checks"]["server"] == ("down" if server is down else "up")
    assert response.json()["checks"]["database"] == (
        "down" if database is down else "up"
    )


def test_database_exception_does_not_leak_or_prevent_health_response(
    app, client, caplog
):
    app.state.health_service = HealthService(up, failed)

    response = client.get("/api/v1/health?server_id=1")

    assert response.status_code == 503
    assert response.json()["checks"] == {"server": "up", "database": "down"}
    assert "dummy-sensitive" not in response.text
    assert "dummy-sensitive" not in caplog.text


def test_timed_out_probe_is_cancelled_and_reported_down():
    cancelled = []

    async def slow() -> bool:
        try:
            await asyncio.sleep(60)
            return True
        finally:
            cancelled.append(True)

    service = HealthService(up, slow, timeout_seconds=0.01, clock=lambda: CHECKED_AT)
    report = asyncio.run(service.check(1))

    assert report.status == "unhealthy"
    assert report.checks.database == "down"
    assert cancelled == [True]


@pytest.mark.parametrize(
    "method", ["POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
)
def test_health_only_accepts_get(client, method):
    response = client.request(method, "/api/v1/health")

    assert response.status_code == 405
    assert response.headers["allow"] == "GET"
    if method != "HEAD":
        assert response.json()["error"]["code"] == "method_not_allowed"


@pytest.mark.parametrize(
    "url,body",
    [
        ("/api/v1/health?server_id=1&verbose=true", None),
        ("/api/v1/health?server_id=1", b"{}"),
        ("/api/v1/health?server_id=1", b" "),
    ],
)
def test_health_rejects_unknown_query_parameters_and_request_bodies(client, url, body):
    response = client.request("GET", url, content=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize(
    "server_id",
    [
        "-1",
        "0",
        "abc",
        "1.5",
        "",
        " ",
        "1e0",
        "true",
    ],
)
def test_invalid_server_id_returns_400(client, server_id):
    response = client.get("/api/v1/health", params={"server_id": server_id})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


@pytest.mark.parametrize("server_id", ["1", "+1", " 1 ", "01"])
def test_positive_integer_id_returns_200(app, client, server_id):
    app.state.health_service = HealthService(up, up)

    response = client.get("/api/v1/health", params={"server_id": server_id})

    assert response.status_code == 200
    assert response.json()["server_id"] == 1


@pytest.mark.parametrize("server_id", ["9223372036854775808", "9" * 100])
def test_large_positive_id_is_valid_but_unregistered(client, server_id):
    response = client.get("/api/v1/health", params={"server_id": server_id})

    assert response.status_code == 404


def test_duplicate_server_id_returns_400(client):
    response = client.get("/api/v1/health?server_id=1&server_id=2")
    assert response.status_code == 400


def test_missing_server_id_returns_422(client):
    assert client.get("/api/v1/health").status_code == 422


def test_unregistered_server_returns_404_without_running_probes(app, client):
    calls = []

    async def unexpected_probe():
        calls.append(True)
        return True

    app.state.health_service = HealthService(unexpected_probe, unexpected_probe)
    response = client.get("/api/v1/health?server_id=2")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert calls == []


def test_probe_timeout_returns_503(app, client):
    async def slow():
        await asyncio.sleep(60)
        return True

    app.state.health_service = HealthService(slow, up, timeout_seconds=0.01)
    response = client.get("/api/v1/health?server_id=1")
    assert response.status_code == 503
    assert response.json()["server_id"] == 1
    assert response.json()["checks"]["server"] == "down"


def test_unexpected_health_failure_returns_sanitized_500(app, client):
    def broken_clock():
        raise RuntimeError("dummy-sensitive-clock-error")

    app.state.health_service = HealthService(up, up, clock=broken_clock)
    response = client.get("/api/v1/health?server_id=1")
    assert response.status_code == 500
    assert "dummy-sensitive" not in response.text


@pytest.mark.parametrize("healthy", [True, False])
def test_health_usually_responds_within_200_ms(app, client, healthy):
    """Measure local request latency, excluding TestClient startup.

    Check the 95th percentile of 20 requests: the target is for most responses,
    not a guarantee about every request on a busy machine or a remote network.
    """
    if healthy:
        app.state.health_service = HealthService(up, up)
    expected_status = 200 if healthy else 503
    client.get("/api/v1/health?server_id=1")  # Warm up routing and worker threads.

    durations = []
    for _ in range(20):
        start = perf_counter()
        response = client.get("/api/v1/health?server_id=1")
        durations.append(perf_counter() - start)
        assert response.status_code == expected_status

    # The 19th sorted sample is the nearest-rank 95th percentile of 20 samples.
    p95 = sorted(durations)[18]
    assert p95 < 0.2, f"Health response p95 was {p95 * 1000:.1f} ms"


@pytest.mark.parametrize(
    "slow_server,slow_database", [(True, False), (False, True), (True, True)]
)
def test_default_timeout_returns_503_within_200_ms(
    app, client, slow_server, slow_database
):
    """Slow probes must time out concurrently using the production default."""
    cancelled = []

    async def slow():
        try:
            await asyncio.sleep(60)
            return True
        finally:
            cancelled.append(True)

    app.state.health_service = HealthService(
        slow if slow_server else up,
        slow if slow_database else up,
    )

    start = perf_counter()
    response = client.get("/api/v1/health?server_id=1")
    elapsed = perf_counter() - start

    assert response.status_code == 503
    assert response.json()["checks"] == {
        "server": "down" if slow_server else "up",
        "database": "down" if slow_database else "up",
    }
    assert len(cancelled) == int(slow_server) + int(slow_database)
    assert elapsed < 0.2, f"Timed-out health response took {elapsed * 1000:.1f} ms"
