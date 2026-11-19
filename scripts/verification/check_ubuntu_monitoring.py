"""Read-only Ubuntu runtime checks; never display response bodies or secrets."""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from http.client import HTTPConnection
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts/setup"))


class CheckFailed(RuntimeError):
    """A fixed diagnostic that is safe to display."""


def request(path: str, token=None):
    headers = {}
    if token is not None:
        headers["Authorization"] = "Bearer " + token.get_secret_value()
    connection = HTTPConnection("127.0.0.1", 8000, timeout=3)
    try:
        connection.request("GET", "/api/v1" + path, headers=headers)
        response = connection.getresponse()
        body = response.read()
        return response.status, json.loads(body) if body else None
    finally:
        connection.close()


def wait_for_api() -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            request("/server")
            return
        except OSError:
            time.sleep(0.5)
    raise CheckFailed("API did not start within 20 seconds.")


def check_listeners() -> None:
    """Require local-only API/PostgreSQL listeners without changing networking."""
    result = subprocess.run(
        ["ss", "-H", "-ltn", "( sport = :8000 or sport = :5432 )"],
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    )
    ports = set()
    for line in result.stdout.splitlines():
        address = line.split()[3]
        host, port = address.rsplit(":", 1)
        if host.strip("[]") not in {"127.0.0.1", "::1"}:
            raise CheckFailed("API/PostgreSQL listener is not local-only.")
        ports.add(port)
    if ports != {"8000", "5432"}:
        raise CheckFailed("Expected API/PostgreSQL listeners missing.")


def check_database(settings) -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from app.core.database import Database
    from sqlalchemy import inspect, text

    database = Database(settings)
    try:
        with database.engine.connect() as connection:
            inspector = inspect(connection)
            if not {"metrics", "incidents"} <= set(inspector.get_table_names()):
                raise CheckFailed("Required tables missing.")
            head = ScriptDirectory.from_config(
                Config(str(ROOT / "backend/alembic.ini"))
            ).get_current_head()
            if (
                connection.scalar(text("SELECT version_num FROM alembic_version"))
                != head
            ):
                raise CheckFailed("Run setup to apply current migrations.")
    finally:
        database.engine.dispose()


def check_http(settings) -> None:
    from app.schemas.metric import MetricPage
    from app.services.server import read_host_info

    reader = settings.reader_token
    status, server = request("/server", reader)
    if status != 200 or server != {
        "id": 1,
        "name": settings.server_name,
        **read_host_info(),
    }:
        raise CheckFailed("Server API does not identify this host.")
    if request("/server")[0] != 401:
        raise CheckFailed("Server API must require authentication.")
    # Initial PostgreSQL connections can exceed the tight health budget. Retry
    # briefly; never treat a persistent unhealthy response as a successful setup.
    for _ in range(3):
        status, health = request("/health?server_id=1")
        if (
            status == 200
            and health.get("checks") == {"server": "up", "database": "up"}
            and health.get("server_id") == 1
            and health.get("status") == "healthy"
        ):
            break
        time.sleep(1)
    else:
        raise CheckFailed("Health API is unhealthy.")
    if request("/health?server_id=-1")[0] != 400:
        raise CheckFailed("Server ID validation failed.")
    if request("/incidents?limit=1", reader)[0] != 200:
        raise CheckFailed("Incident storage/read access unavailable.")
    print(
        "[PASS] Host identity, authentication, health and incident storage", flush=True
    )

    def latest():
        status, body = request("/metrics?limit=1", reader)
        if status != 200:
            raise CheckFailed("Metrics unavailable; check migration and reader token.")
        page = MetricPage.model_validate(body)
        return page.items[0] if page.items else None

    initial = latest()
    baseline = initial.id if initial is not None else None
    started = datetime.now(UTC)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        sample = latest()
        if sample is not None and sample.id != baseline:
            now = datetime.now(UTC)
            if started <= sample.collected_at <= now:
                print(
                    "[PASS] A new host measurement was persisted during verification",
                    flush=True,
                )
                return
        time.sleep(1)
    raise CheckFailed(
        "No fresh measurement arrived within 30s; check collector service and token."
    )


def main() -> None:
    from configure_ubuntu import validate

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    for name in list(os.environ):
        if name.startswith("SERVERWATCH_"):
            del os.environ[name]
    stage = "private configuration (ownership, permissions, distinct role tokens)"
    try:
        settings = validate(args.config)
        print("[PASS] Private managed configuration and role credentials", flush=True)
        stage = "API startup (up to 20s); inspect serverwatch-api service"
        wait_for_api()
        stage = "local-only API/PostgreSQL listeners"
        check_listeners()
        print("[PASS] API and PostgreSQL listen only on loopback", flush=True)
        stage = "database connectivity/migration version; rerun setup if needed"
        check_database(settings)
        print(
            "[PASS] PostgreSQL connection, both tables and current migration",
            flush=True,
        )
        stage = "API responses and fresh metrics (up to 30s); inspect service journals"
        check_http(settings)
    except CheckFailed as error:
        raise SystemExit(f"[FAIL] {error}") from None
    except Exception:
        raise SystemExit(
            f"[FAIL] Check {stage}. Details withheld to protect credentials."
        ) from None


if __name__ == "__main__":
    main()
