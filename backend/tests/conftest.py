"""Isolated application fixtures; no external services or dotenv files."""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

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
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def app() -> FastAPI:
    return create_app(Settings(app_name="ServerWatch tests", environment="test"))


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
