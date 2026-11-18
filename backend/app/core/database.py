"""PostgreSQL connectivity without exposing credentials or blocking requests."""

from psycopg import AsyncConnection
from pydantic import SecretStr

from app.core.config import Settings


class Database:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.password = settings.database_password
        if settings.database_password_file is not None:
            try:
                self.password = SecretStr(
                    settings.database_password_file.read_text(encoding="utf-8").strip()
                )
            except (OSError, UnicodeError):
                raise RuntimeError(
                    "Cannot read configured database password file."
                ) from None

        if self.password is not None and not self.password.get_secret_value():
            raise RuntimeError("Configured database password must not be empty.")

    async def check(self) -> bool:
        """Open a short-lived connection and verify that PostgreSQL answers.

        The health service enforces its existing async timeout and sanitizes
        connection failures. No password means unconfigured, so no connection
        is attempted. The context manager closes connections on every exit.
        Tables and a shared connection pool are separate persistence work.
        """
        if self.password is None:
            return False

        async with await AsyncConnection.connect(
            host=self.settings.database_host,
            port=self.settings.database_port,
            dbname=self.settings.database_name,
            user=self.settings.database_user,
            password=self.password.get_secret_value(),
            autocommit=True,
            connect_timeout=2,
            options="-c statement_timeout=100",
        ) as connection:
            cursor = await connection.execute("SELECT 1")
            return await cursor.fetchone() == (1,)
