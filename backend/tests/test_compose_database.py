"""Exercise fresh and legacy Compose roles against a disposable PostgreSQL."""

import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from conftest import private_postgres_engine
from psycopg import connect
from psycopg.errors import InsufficientPrivilege
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "compose_database", ROOT / "infrastructure/docker/provision_database.py"
)
assert SPEC and SPEC.loader
roles = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(roles)

PASSWORDS = {
    "db_password": "test-app-password",
    "db_migration_password": "test-migration-password",
}

INSERT_METRIC = """
    INSERT INTO metrics VALUES (%s, '1', now(), 12, 23, 34, 100)
"""
INSERT_INCIDENT = """
    INSERT INTO incidents (id, server_id, title, description, severity, status,
                           occurred_at, created_at, updated_at)
    VALUES (%s, '1', 'Test', 'Test description', 'info', 'open', now(), now(), now())
"""


def migrate(url, user, password):
    engine = create_engine(url.set(username=user, password=password))
    try:
        with engine.begin() as connection:
            config = Config(str(ROOT / "backend/alembic.ini"))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
    finally:
        engine.dispose()


@pytest.mark.parametrize("legacy", [False, True], ids=["fresh", "existing-volume"])
def test_compose_role_split(legacy, tmp_path_factory, monkeypatch):
    role_password = (
        "SELECT rolpassword FROM pg_authid WHERE rolname = 'serverwatch_app'"
    )
    monkeypatch.setattr(roles, "read_secret", PASSWORDS.__getitem__)
    with private_postgres_engine(tmp_path_factory) as cluster:
        url = cluster.url.set(database="serverwatch")

        def login(user, password=None):
            return connect(
                host=url.host,
                port=url.port,
                dbname=url.database,
                user=user,
                password=password,
            )

        with cluster.connect().execution_options(isolation_level="AUTOCOMMIT") as admin:
            admin.exec_driver_sql("CREATE ROLE postgres LOGIN SUPERUSER")
            admin.exec_driver_sql("CREATE DATABASE serverwatch OWNER postgres")
        metric_id, incident_id = uuid4(), uuid4()
        if legacy:
            with login("postgres") as admin:
                admin.execute(
                    "CREATE ROLE serverwatch_app LOGIN PASSWORD 'test-app-password'"
                )
                admin.execute("ALTER DATABASE serverwatch OWNER TO serverwatch_app")
                previous_password = admin.execute(role_password).fetchone()
            migrate(url, roles.APP, PASSWORDS["db_password"])
            with login(roles.APP, PASSWORDS["db_password"]) as app:
                app.execute(INSERT_METRIC, (metric_id,))
                app.execute(INSERT_INCIDENT, (incident_id,))

        for _ in range(2):
            with login("postgres") as admin:
                roles.provision(admin)
                if legacy:
                    assert previous_password == admin.execute(role_password).fetchone()
            migrate(url, roles.MIGRATOR, PASSWORDS["db_migration_password"])
            with login(roles.MIGRATOR, PASSWORDS["db_migration_password"]) as migrator:
                roles.grant_runtime(migrator)
                assert migrator.execute(
                    "SELECT pg_get_userbyid(nspowner) FROM pg_namespace "
                    "WHERE nspname = 'public'"
                ).fetchone() == (roles.MIGRATOR,)
                assert migrator.execute(
                    "SELECT DISTINCT tableowner FROM pg_tables "
                    "WHERE schemaname = 'public'"
                ).fetchall() == [(roles.MIGRATOR,)]

        with login(roles.APP, PASSWORDS["db_password"]) as app:
            if legacy:
                assert app.execute("SELECT id FROM metrics").fetchone() == (metric_id,)
                assert app.execute("SELECT id FROM incidents").fetchone() == (
                    incident_id,
                )
            else:
                app.execute(INSERT_METRIC, (metric_id,))
                app.execute(INSERT_INCIDENT, (incident_id,))
            assert app.execute("SELECT cpu_percent FROM metrics").fetchone() == (12,)
            assert app.execute(
                "UPDATE incidents SET title = 'Changed' WHERE id = %s RETURNING title",
                (incident_id,),
            ).fetchone() == ("Changed",)
            assert (
                app.execute(
                    "DELETE FROM incidents WHERE id = %s", (incident_id,)
                ).rowcount
                == 1
            )
            for statement in (
                "ALTER TABLE metrics ADD COLUMN forbidden int",
                "DROP TABLE incidents",
                "CREATE TABLE forbidden (id int)",
                "DELETE FROM metrics",
                "SELECT * FROM alembic_version",
            ):
                with pytest.raises(InsufficientPrivilege), app.transaction():
                    app.execute(statement)
