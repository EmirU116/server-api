"""Preview the actual migration command using dummy configuration only."""

import os
import subprocess
import sys
from pathlib import Path


def test_migration_cli_can_preview_sql_without_database():
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parents[1] / "migrate.py"), "--sql"],
        env={
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "SERVERWATCH_DATABASE_PASSWORD": "dummy-private-password",
        },
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0
    assert "CREATE TABLE metrics" in result.stdout
    assert "dummy-private-password" not in result.stdout + result.stderr
