"""Apply reviewed schema upgrades using explicit private environment loading."""

import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument(
        "--sql", action="store_true", help="Print SQL without connecting"
    )
    args = parser.parse_args()
    if args.env_file is not None:
        if not args.env_file.is_file():
            raise SystemExit("Configured environment file does not exist.")
        load_dotenv(args.env_file, override=False)
    config = Config(str(Path(__file__).with_name("alembic.ini")))
    try:
        command.upgrade(config, "head", sql=args.sql)
    except Exception:
        # Driver/migration exceptions may contain SQL or connection details.
        raise SystemExit(
            "Migration failed. Check database settings, access, and schema version."
        ) from None


if __name__ == "__main__":
    main()
