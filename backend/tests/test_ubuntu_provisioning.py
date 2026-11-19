"""Verify Ubuntu's SQL and SCRAM password using disposable PostgreSQL only."""

import importlib.util
import shutil
import subprocess
from pathlib import Path

import psycopg
import pytest
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]


def test_provisioning_preserves_password_and_records_on_rerun(
    postgres_engine, tmp_path
):
    spec = importlib.util.spec_from_file_location(
        "configure_ubuntu", ROOT / "scripts/setup/configure_ubuntu.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = tmp_path / "managed"
    module.prepare(config)
    psql = shutil.which("psql")
    if psql is None:
        pytest.skip("psql required for provisioning integration")
    url = postgres_engine.url
    command = [
        psql,
        "-X",
        "-q",
        "-v",
        "ON_ERROR_STOP=1",
        "-h",
        url.host,
        "-p",
        str(url.port),
        "-U",
        url.username,
        "-d",
        url.database,
    ]
    for _ in range(2):
        result = subprocess.run(
            command,
            input=module.database_sql(config),
            text=True,
            capture_output=True,
            timeout=10,
        )
        assert result.returncode == 0
    with postgres_engine.connect() as connection:
        verifier = connection.scalar(
            text(
                "SELECT rolpassword FROM pg_authid "
                "WHERE rolname = 'serverwatch_monitor'"
            )
        )
        assert verifier.startswith("SCRAM-SHA-256$")
    # Require actual SCRAM authentication for the new role in this disposable
    # cluster, leaving the fixture administrator's trust rule unchanged.
    import time

    with postgres_engine.connect() as connection:
        hba = Path(connection.scalar(text("SHOW hba_file")))
    hba.write_text(
        "host serverwatch_monitor serverwatch_monitor 127.0.0.1/32 scram-sha-256\n"
        + hba.read_text()
    )
    with postgres_engine.connect() as connection:
        connection.execute(text("SELECT pg_reload_conf()"))
    time.sleep(0.2)
    password = (config / "db_password").read_text().strip()
    with pytest.raises(psycopg.OperationalError):
        psycopg.connect(
            host=url.host,
            port=url.port,
            dbname=module.DATABASE,
            user=module.DATABASE,
            password="dummy-wrong-password",
        )
    with psycopg.connect(
        host=url.host,
        port=url.port,
        dbname=module.DATABASE,
        user=module.DATABASE,
        password=password,
        autocommit=True,
    ) as connection:
        connection.execute("CREATE TABLE preserved (value integer)")
        connection.execute("INSERT INTO preserved VALUES (42)")
    result = subprocess.run(
        command,
        input=module.database_sql(config),
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0
    with psycopg.connect(
        host=url.host,
        port=url.port,
        dbname=module.DATABASE,
        user=module.DATABASE,
        password=password,
    ) as connection:
        assert connection.execute("SELECT value FROM preserved").fetchone() == (42,)
