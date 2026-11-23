"""Assign schema ownership and runtime grants for the Compose database."""

import sys
from pathlib import Path

from psycopg import Error, connect, sql
from psycopg.errors import InvalidAuthorizationSpecification

APP = "serverwatch_app"
MIGRATOR = "serverwatch_migrator"
TABLES = ("metrics", "incidents", "alembic_version")


def read_secret(name: str) -> str:
    value = Path("/run/secrets", name).read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError("Empty PostgreSQL credential.")
    return value


def provision(connection) -> None:
    # Retain existing passwords and transfer only objects used by this stack.
    connection.execute("SELECT pg_advisory_xact_lock(41825)")
    for role, secret in ((APP, "db_password"), (MIGRATOR, "db_migration_password")):
        exists = connection.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)
        ).fetchone()
        if exists is None:
            connection.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(role), sql.Literal(read_secret(secret))
                )
            )

    connection.execute("ALTER DATABASE serverwatch OWNER TO postgres")
    connection.execute("REVOKE CREATE, TEMPORARY ON DATABASE serverwatch FROM PUBLIC")
    connection.execute("ALTER SCHEMA public OWNER TO serverwatch_migrator")
    connection.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
    connection.execute("GRANT USAGE ON SCHEMA public TO serverwatch_app")

    for table in TABLES:
        connection.execute(
            sql.SQL(
                "ALTER TABLE IF EXISTS public.{} OWNER TO serverwatch_migrator"
            ).format(sql.Identifier(table))
        )
    # Keep existing tables accessible while Alembic runs on upgrades.
    grant_runtime(connection)


def grant_runtime(connection) -> None:
    for table, privileges in (
        ("metrics", "SELECT, INSERT"),
        ("incidents", "SELECT, INSERT, UPDATE, DELETE"),
    ):
        if connection.execute(
            "SELECT to_regclass(%s)", (f"public.{table}",)
        ).fetchone()[0]:
            connection.execute(
                sql.SQL("GRANT {} ON TABLE public.{} TO serverwatch_app").format(
                    sql.SQL(privileges), sql.Identifier(table)
                )
            )


def main() -> None:
    grant_only = sys.argv[1:] == ["grant-runtime"]
    user, secret = (
        (MIGRATOR, "db_migration_password")
        if grant_only
        else ("postgres", "db_admin_password")
    )
    try:
        with connect(
            host="db",
            dbname="serverwatch",
            user=user,
            password=read_secret(secret),
            connect_timeout=5,
        ) as connection:
            if grant_only:
                grant_runtime(connection)
            else:
                provision(connection)
    except InvalidAuthorizationSpecification:
        raise SystemExit(
            "Compose database provisioning authentication failed."
        ) from None
    except (Error, OSError, ValueError):
        raise SystemExit(
            "Could not assign Compose database ownership and grants."
        ) from None


if __name__ == "__main__":
    main()
