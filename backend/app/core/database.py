"""PostgreSQL connectivity without exposing credentials or blocking requests."""

from psycopg import AsyncConnection
from sqlalchemy import URL, create_engine

from app.core.config import Settings, read_secret_file


class Database:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.password = settings.database_password
        if settings.database_password_file is not None:
            self.password = read_secret_file(
                settings.database_password_file, "database password"
            )

        if self.password is not None and not self.password.get_secret_value():
            raise RuntimeError("Configured database password must not be empty.")

        # Constructing an engine does not connect. Credentials stay out of URLs
        # rendered in logs, and SQL parameter values are hidden in errors.
        self.engine = None
        if self.password is not None:
            self.engine = create_engine(
                URL.create(
                    "postgresql+psycopg",
                    username=settings.database_user,
                    password=self.password.get_secret_value(),
                    host=settings.database_host,
                    port=settings.database_port,
                    database=settings.database_name,
                ),
                hide_parameters=True,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=5,
                pool_timeout=3,
                connect_args={
                    "connect_timeout": 2,
                    "options": "-c statement_timeout=3000 -c lock_timeout=2000",
                },
            )

    async def check(self) -> bool:
        """Open a short-lived connection and verify that PostgreSQL answers.

        The health service enforces its existing async timeout and sanitizes
        connection failures. No password means unconfigured, so no connection
        is attempted. The context manager closes connections on every exit.
        Metrics use a separate SQLAlchemy connection pool and migrations.
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
