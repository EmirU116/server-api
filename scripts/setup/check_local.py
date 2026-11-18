"""Validate local configuration and storage without printing secret values."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def check(env_file: Path, configuration_only: bool = False) -> None:
    """Read secrets only when the user launches this local verification script.

    Configuration checks run before touching a Windows service. Database checks
    prove the configured login can read metrics, without writing records or
    applying migrations. Loading .env occurs only in this short-lived process.
    """
    import psutil
    from app.main import create_app
    from app.models.metric import Metric
    from dotenv import load_dotenv
    from sqlalchemy import select

    if not env_file.is_file():
        raise RuntimeError("Create a private .env using the local PostgreSQL guide.")
    load_dotenv(env_file, override=False)
    app = create_app()
    database = app.state.database
    try:
        if app.state.settings.database_host not in {"localhost", "127.0.0.1", "::1"}:
            raise RuntimeError("The local launcher requires a local database host.")
        if app.state.settings.environment != "development":
            raise RuntimeError("Use SERVERWATCH_ENVIRONMENT=development locally.")
        if database.engine is None:
            raise RuntimeError("Configure the database password privately in .env.")
        if app.state.reader_token is None:
            raise RuntimeError("Configure a reader token privately in .env.")
        if app.state.collector_token is None:
            raise RuntimeError(
                "Configure a separate collector token privately in .env."
            )
        # Importing psutil here also checks its platform-specific binary before
        # the launcher starts PostgreSQL or either application.
        psutil.cpu_count()
        if not configuration_only:
            with database.engine.connect() as connection:
                connection.execute(select(Metric.id).limit(0))
    finally:
        if database.engine is not None:
            database.engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--configuration-only", action="store_true")
    args = parser.parse_args()
    try:
        check(args.env_file, args.configuration_only)
    except Exception:
        # Never echo driver exceptions, settings, submitted values, or .env text.
        print(
            "FAIL: Local configuration/storage check failed. Check Python "
            "dependencies, .env, local PostgreSQL, reader/collector tokens, "
            "and the metrics migration. See docs/local-development.md.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    print(
        "PASS: Local configuration"
        if args.configuration_only
        else "PASS: Database and metrics table"
    )


if __name__ == "__main__":
    main()
