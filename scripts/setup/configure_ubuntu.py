"""Private configuration and database provisioning inputs for Ubuntu setup.

This helper is called by setup_ubuntu_monitoring.sh. It never reads the local
project .env or replaces existing credentials. The SQL action is piped directly
into psql and must never be run with shell tracing or displayed in a terminal.
"""

import argparse
import base64
import hashlib
import hmac
import os
import secrets
import sys
from pathlib import Path

# Tests load this file by path, so make its sibling helper importable.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from private_files import private_directory, private_file, require_private  # noqa: E402

DATABASE = "serverwatch_monitor"


def prepare(config: Path) -> None:
    private_directory(config)
    for name in ("reader_token", "collector_token", "admin_token", "db_password"):
        private_file(config / name, secrets.token_urlsafe(32) + "\n")
    private_file(
        config / "api.env",
        f"""SERVERWATCH_ENVIRONMENT=production
SERVERWATCH_SERVER_ID=1
SERVERWATCH_SERVER_NAME=ServerWatch Ubuntu
SERVERWATCH_DATABASE_HOST=127.0.0.1
SERVERWATCH_DATABASE_PORT=5432
SERVERWATCH_DATABASE_NAME={DATABASE}
SERVERWATCH_DATABASE_USER={DATABASE}
SERVERWATCH_DATABASE_PASSWORD_FILE={config}/db_password
SERVERWATCH_READER_TOKEN_FILE={config}/reader_token
SERVERWATCH_COLLECTOR_TOKEN_FILE={config}/collector_token
SERVERWATCH_ADMIN_TOKEN_FILE={config}/admin_token
PYTHONDONTWRITEBYTECODE=1
""",
    )
    # The collector receives only its submission credential, not database/admin
    # secrets. Both processes currently run as the installing SSH user.
    private_file(
        config / "collector.env",
        f"SERVERWATCH_COLLECTOR_TOKEN_FILE={config}/collector_token\n",
    )
    validate(config)


def validate(config: Path):
    from app.core.config import Settings
    from app.core.security import load_token
    from dotenv import dotenv_values
    from pydantic import SecretStr

    # Read only the managed file: ambient SERVERWATCH_* variables and a cloned
    # .env cannot redirect this installer to a remote/production database.
    require_private(config, directory=True)
    for name in (
        "reader_token",
        "collector_token",
        "admin_token",
        "db_password",
        "api.env",
        "collector.env",
    ):
        require_private(config / name)
    values = dotenv_values(config / "api.env")
    expected = {
        "SERVERWATCH_ENVIRONMENT": "production",
        "SERVERWATCH_SERVER_ID": "1",
        "SERVERWATCH_DATABASE_HOST": "127.0.0.1",
        "SERVERWATCH_DATABASE_PORT": "5432",
        "SERVERWATCH_DATABASE_NAME": DATABASE,
        "SERVERWATCH_DATABASE_USER": DATABASE,
        "SERVERWATCH_DATABASE_PASSWORD_FILE": str(config / "db_password"),
        **{
            f"SERVERWATCH_{role.upper()}_TOKEN_FILE": str(config / f"{role}_token")
            for role in ("reader", "collector", "admin")
        },
    }
    if any(values.get(name) != value for name, value in expected.items()):
        raise RuntimeError(
            "Existing managed configuration does not match this installer."
        )
    allowed = set(expected) | {"SERVERWATCH_SERVER_NAME", "PYTHONDONTWRITEBYTECODE"}
    if set(values) - allowed:
        raise RuntimeError("Unsupported managed configuration fields.")
    tokens = []
    for role in ("reader", "collector", "admin"):
        token = load_token(None, config / f"{role}_token", role)
        tokens.append(token.get_secret_value())
    if len(set(tokens)) != 3:
        raise RuntimeError("Role tokens must be different.")
    password = (config / "db_password").read_text().strip()
    if not password:
        raise RuntimeError("Database password is empty.")
    collector = dotenv_values(config / "collector.env")
    if collector != {
        "SERVERWATCH_COLLECTOR_TOKEN_FILE": str(config / "collector_token")
    }:
        raise RuntimeError("Collector configuration must contain only its token file.")
    return Settings(
        _env_file=None,
        environment="production",
        server_id=1,
        server_name=values["SERVERWATCH_SERVER_NAME"],
        database_host="127.0.0.1",
        database_port=5432,
        database_name=DATABASE,
        database_user=DATABASE,
        database_password=SecretStr(password),
        reader_token=SecretStr(tokens[0]),
        collector_token=SecretStr(tokens[1]),
        admin_token=SecretStr(tokens[2]),
    )


def password_verifier(password: str) -> str:
    """Encode PostgreSQL's SCRAM-SHA-256 verifier without sending plaintext SQL.

    PostgreSQL accepts this standard stored verifier in CREATE ROLE PASSWORD.
    The clear password stays in the private file and process memory.
    """
    salt = secrets.token_bytes(16)
    salted = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 4096)
    client_key = hmac.digest(salted, b"Client Key", "sha256")
    stored_key = hashlib.sha256(client_key).digest()
    server_key = hmac.digest(salted, b"Server Key", "sha256")
    salt_text, stored_text, server_text = (
        base64.b64encode(value).decode() for value in (salt, stored_key, server_key)
    )
    return f"SCRAM-SHA-256$4096:{salt_text}${stored_text}:{server_text}"


def database_sql(config: Path) -> str:
    settings = validate(config)
    verifier = password_verifier(settings.database_password.get_secret_value())
    # The fixed role/database names prevent arbitrary identifiers. Existing roles
    # and databases are preserved; later checks reject mismatched credentials.
    return rf"""SELECT 'CREATE ROLE {DATABASE} LOGIN NOSUPERUSER NOCREATEDB '
|| 'NOCREATEROLE NOREPLICATION PASSWORD ' || quote_literal('{verifier}')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{DATABASE}')
\gexec
SELECT 'CREATE DATABASE {DATABASE} OWNER {DATABASE}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '{DATABASE}')
\gexec
DO $$ BEGIN
IF EXISTS (SELECT FROM pg_roles WHERE rolname = '{DATABASE}'
AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls))
OR NOT EXISTS (SELECT FROM pg_database d JOIN pg_roles r ON d.datdba = r.oid
WHERE d.datname = '{DATABASE}' AND r.rolname = '{DATABASE}')
THEN RAISE EXCEPTION 'Existing database or role is incompatible'; END IF;
END $$;
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "database-sql", "validate"))
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    # Managed installation deliberately ignores all ambient application settings.
    for name in list(os.environ):
        if name.startswith("SERVERWATCH_"):
            del os.environ[name]
    try:
        if args.action == "prepare":
            prepare(args.config)
        elif args.action == "database-sql":
            print(database_sql(args.config))
        else:
            validate(args.config)
    except Exception:
        raise SystemExit(
            "[FAIL] Managed configuration is missing, incompatible, or not private. "
            "Existing files were preserved."
        ) from None


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
    main()
