"""Create the Compose database application role once, ahead of Alembic."""

from pathlib import Path

from psycopg import Error, connect, sql
from psycopg.errors import InvalidAuthorizationSpecification


def read_secret(name: str) -> str:
    value = Path("/run/secrets", name).read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError("Empty PostgreSQL credential.")
    return value


def main() -> None:
    try:
        with connect(
            host="db",
            dbname="serverwatch",
            user="postgres",
            password=read_secret("db_admin_password"),
            connect_timeout=5,
        ) as connection:
            # Serialize provisioning, and never reset an existing role's password.
            connection.execute("SELECT pg_advisory_xact_lock(41825)")
            role = connection.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = 'serverwatch_app'"
            ).fetchone()
            if role is None:
                connection.execute(
                    sql.SQL("CREATE ROLE serverwatch_app LOGIN PASSWORD {}").format(
                        sql.Literal(read_secret("db_password"))
                    )
                )
                connection.execute("ALTER DATABASE serverwatch OWNER TO serverwatch_app")
    except InvalidAuthorizationSpecification:
        raise SystemExit("Compose database administrator authentication failed.") from None
    except (Error, OSError, ValueError):
        raise SystemExit("Could not provision the Compose database application role.") from None


if __name__ == "__main__":
    main()
