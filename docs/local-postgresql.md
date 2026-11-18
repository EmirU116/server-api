# Connect FastAPI to local PostgreSQL

PostgreSQL must already contain database `serverwatch`, owned by login
`serverwatch_app`. This guide assumes both PostgreSQL and FastAPI run on Windows.
No Docker is needed. WSL may require a different database host address.

For a single command after setup, see the [local stack launcher](local-development.md).
It starts/reuses Windows PostgreSQL and launches FastAPI and React together.

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
Metrics use a separate bounded SQLAlchemy connection pool (five connections plus
five overflow connections per application process), with a three-second pool
wait and statement timeout, and a two-second connection/lock timeout. See the
[Psycopg async documentation](https://www.psycopg.org/psycopg3/docs/advanced/async.html).

- No configured password: database check remains down; no connection is attempted.
- Invalid password, unavailable database, insufficient access, or timeout: HTTP
  503 with database down. Exception details and credentials are not returned.
- An explicitly empty password or unreadable password file prevents startup.
- For 503, check the PostgreSQL Windows service is running, database/user names
  match, and port 5432 is correct. Try the same login in SQL Shell first.

The user has verified local health against Windows PostgreSQL. Automated tests
also verify metrics against a separate temporary PostgreSQL cluster when server
tools are installed. They never use your existing database or private `.env`.

## Enable metrics storage (Python, PostgreSQL, Alembic)

Install updated dependencies with the same Windows Python used to run FastAPI:

```powershell
.\.venv-windows\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv-windows\Scripts\python.exe backend/migrate.py --env-file .env
```

The migration creates `metrics` and Alembic's version table. It does not run on
application startup. Repeating the upgrade preserves existing records. To inspect
SQL without connecting, add `--sql`. Do not run downgrades against data you need.
Missing tables make metrics return `503`, even when the health query succeeds.
Health verifies connectivity; it does not verify the schema version.

In your private `.env`, configure two different nonblank tokens:

```dotenv
SERVERWATCH_READER_TOKEN=REPLACE_WITH_PRIVATE_READER_TOKEN
SERVERWATCH_COLLECTOR_TOKEN=REPLACE_WITH_DIFFERENT_PRIVATE_COLLECTOR_TOKEN
```

Both also support `_FILE` alternatives in `.env.example`. Restart FastAPI after
editing credentials. Nothing in this setup creates real tokens automatically.

- Readers can GET server information and metrics.
- Collectors can POST metrics. They cannot read protected dashboard endpoints.
- Using a valid token for the wrong role returns `403`; missing/invalid tokens
  return `401`. Missing required role configuration fails closed with `503`.
- The same token cannot be assigned to both roles.

## Verify POST and GET (FastAPI, React)

1. Open <http://127.0.0.1:8000/docs> and click **Authorize**. Enter your collector
   token privately (the token itself, without a `Bearer ` prefix).
2. Execute `POST /api/v1/metrics` with a sample:

   ```json
   {
     "collected_at": "2026-01-01T12:00:00Z",
     "cpu_percent": 27.5,
     "memory_percent": 61.2,
     "disk_percent": 43.8,
     "uptime_seconds": 86400
   }
   ```

   Expect `201` and a generated UUID. Use a different past collection timestamp
   for each sample; repeating the timestamp returns `409`.
3. Switch Swagger authorization to your reader token. Execute GET metrics and
   verify the saved record. `?limit=1` returns the latest sample.
4. Start the frontend with `npm run dev` in `frontend/`, open
   <http://127.0.0.1:5173>, choose **Connect API**, and enter the reader token.
   Health, server information, and saved metrics now load from FastAPI. Incidents
   remain explicitly unavailable. API mode polls every five seconds. The sample
   above is manually supplied test data. For real host measurements, use the
   [local launcher and collector](local-development.md); the launcher now starts
   the collector automatically after the API.

Never enter the collector token or database password into the frontend.
For automated verification, run `python -m pytest backend/tests -q`. The database
integration tests start and stop a private loopback-only cluster under pytest's
temporary directory. Without `initdb`/`pg_ctl`, they skip; API unit tests still run.
