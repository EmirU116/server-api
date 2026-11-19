"""Isolated application fixtures; no external services or dotenv files."""

import os
import shutil
import socket
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine

from app.core.config import Settings
from app.main import create_app


@pytest.fixture(autouse=True)
def isolate_server_configuration(monkeypatch):
    """Never load a developer's reader token file or host identity in tests."""
    for name in (
        "SERVERWATCH_SERVER_ID",
        "SERVERWATCH_SERVER_NAME",
        "SERVERWATCH_READER_TOKEN",
        "SERVERWATCH_READER_TOKEN_FILE",
        "SERVERWATCH_ADMIN_TOKEN",
        "SERVERWATCH_ADMIN_TOKEN_FILE",
        "SERVERWATCH_COLLECTOR_TOKEN",
        "SERVERWATCH_COLLECTOR_TOKEN_FILE",
        "SERVERWATCH_DATABASE_HOST",
        "SERVERWATCH_DATABASE_PORT",
        "SERVERWATCH_DATABASE_NAME",
        "SERVERWATCH_DATABASE_USER",
        "SERVERWATCH_DATABASE_PASSWORD",
        "SERVERWATCH_DATABASE_PASSWORD_FILE",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def app() -> FastAPI:
    return create_app(Settings(app_name="ServerWatch tests", environment="test"))


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def postgres_engine(tmp_path_factory):
    initdb = shutil.which("initdb")
    if initdb is None:
        candidates = sorted(Path("/usr/lib/postgresql").glob("*/bin/initdb"))
        initdb = str(candidates[-1]) if candidates else None
    if initdb is None or (hasattr(os, "geteuid") and os.geteuid() == 0):
        pytest.skip("PostgreSQL initdb/pg_ctl and a non-root account are required")

    folder = tmp_path_factory.mktemp("serverwatch-private-postgres")
    data = folder / "data"
    pg_ctl = str(Path(initdb).with_name("pg_ctl"))
    subprocess.run(
        [
            initdb,
            "-D",
            str(data),
            "-U",
            "serverwatch_test",
            "-A",
            "trust",
            "--no-locale",
            "-E",
            "UTF8",
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    # Trust authentication is confined to this short-lived, loopback-only test
    # cluster. Its files and sockets are under pytest's private temp directory.
    subprocess.run(
        [
            pg_ctl,
            "-D",
            str(data),
            "-l",
            str(folder / "postgres.log"),
            "-o",
            f"-F -h 127.0.0.1 -p {port} -k {folder}",
            "-w",
            "start",
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    engine = create_engine(
        URL.create(
            "postgresql+psycopg",
            username="serverwatch_test",
            host="127.0.0.1",
            port=port,
            database="postgres",
        )
    )
    try:
        config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            command.upgrade(config, "head")  # Repeating an upgrade preserves schema.
        yield engine
    finally:
        engine.dispose()
        subprocess.run(
            [pg_ctl, "-D", str(data), "-m", "fast", "-w", "stop"],
            check=True,
            capture_output=True,
            timeout=30,
        )
