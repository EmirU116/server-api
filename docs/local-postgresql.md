# Connect FastAPI to local PostgreSQL

PostgreSQL must already contain database `serverwatch`, owned by login
`serverwatch_app`. This guide assumes both PostgreSQL and FastAPI run on Windows.
No Docker is needed. WSL may require a different database host address.

## Windows PowerShell

From the repository root, create a Windows virtual environment. Keep it separate
from any Linux/WSL `.venv`:

```powershell
py -m venv .venv-windows
.\.venv-windows\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
```

If `.env` does not exist, copy the template. This command preserves an existing file:

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

Set these values privately in `.env` (replace the password placeholder):

```dotenv
SERVERWATCH_DATABASE_HOST=localhost
SERVERWATCH_DATABASE_PORT=5432
SERVERWATCH_DATABASE_NAME=serverwatch
SERVERWATCH_DATABASE_USER=serverwatch_app
SERVERWATCH_DATABASE_PASSWORD='REPLACE_LOCALLY'
```

Use the password you assigned to `serverwatch_app`. Keep it out of Git and chat.
Individual settings avoid URL-encoding passwords. Dotenv quoting rules still
apply; for passwords containing quotes or escapes, use a protected password file
with `SERVERWATCH_DATABASE_PASSWORD_FILE` instead. File configuration takes
precedence over the password environment variable.

Start the application:

```powershell
.\.venv-windows\Scripts\python.exe -m uvicorn app.main:create_app --factory --app-dir backend --env-file .env --reload --host 127.0.0.1 --port 8000
```

In another PowerShell window:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/health?server_id=1'
```

Expected: HTTP 200, `status: healthy`, and both checks `up`.
The reader token is not required for health.

## Behavior and troubleshooting

FastAPI uses Psycopg's asynchronous connection API to execute `SELECT 1` and
closes the connection afterward. The existing 150 ms health-probe timeout still
applies; PostgreSQL's statement timeout is 100 ms. Each request opens a new
connection, so initial connections or busy hosts may exceed the health budget.
Connection pooling is future persistence work. See the
[Psycopg async documentation](https://www.psycopg.org/psycopg3/docs/advanced/async.html).

- No configured password: database check remains down; no connection is attempted.
- Invalid password, unavailable database, insufficient access, or timeout: HTTP
  503 with database down. Exception details and credentials are not returned.
- An explicitly empty password or unreadable password file prevents startup.
- For 503, check the PostgreSQL Windows service is running, database/user names
  match, and port 5432 is correct. Try the same login in SQL Shell first.

This implements connectivity, not stored server/metrics/incident records.
SQLAlchemy models, Alembic migrations, and persistence APIs remain pending.
Automated backend tests use fake connections and dummy secrets; successful
connectivity to your actual Windows database must be verified on your computer.
