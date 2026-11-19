"""Use fake connections and dummy credentials; never contact a real database."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.database import Database
from app.main import create_app


def test_missing_password_does_not_connect():
    with patch("app.core.database.AsyncConnection.connect") as connect:
        assert asyncio.run(Database(Settings()).check()) is False
        connect.assert_not_called()


@pytest.mark.parametrize("result,expected", [((1,), True), (None, False)])
def test_query_and_connection_cleanup(result, expected):
    connection = AsyncMock()
    connection.execute.return_value.fetchone.return_value = result
    context = AsyncMock()
    context.__aenter__.return_value = connection
    with patch(
        "app.core.database.AsyncConnection.connect", new_callable=AsyncMock
    ) as connect:
        connect.return_value = context
        database = Database(Settings(database_password=SecretStr("dummy-password")))
        assert asyncio.run(database.check()) is expected
        connection.execute.assert_awaited_once_with("SELECT 1")
        context.__aexit__.assert_awaited_once()


@pytest.mark.parametrize("failure", [False, True])
def test_health_uses_database_probe(client, app, failure, caplog):
    with patch(
        "app.core.database.AsyncConnection.connect", new_callable=AsyncMock
    ) as connect:
        database = Database(Settings(database_password=SecretStr("dummy-password")))
        app.state.health_service.database_probe = database.check
        if failure:
            connect.side_effect = RuntimeError("dummy-password connection failed")
        else:
            connection = AsyncMock()
            connection.execute.return_value.fetchone.return_value = (1,)
            connect.return_value.__aenter__.return_value = connection
        response = client.get("/api/v1/health?server_id=1")
        assert response.status_code == (503 if failure else 200)
        assert response.json()["checks"]["database"] == ("down" if failure else "up")
        assert "dummy-password" not in response.text + caplog.text


def test_password_file_takes_precedence(tmp_path):
    path = tmp_path / "dummy-password"
    path.write_text("file-password\n")
    database = Database(
        Settings(
            database_password=SecretStr("env-password"), database_password_file=path
        )
    )
    assert database.password.get_secret_value() == "file-password"


def test_unreadable_password_file_fails_safely(tmp_path):
    with pytest.raises(RuntimeError, match="Cannot read configured database password"):
        create_app(Settings(database_password_file=tmp_path / "absent"))


def test_empty_password_prevents_startup():
    with pytest.raises(RuntimeError, match="must not be empty"):
        create_app(Settings(database_password=SecretStr("")))
