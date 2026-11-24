# Start the local stack (Bash, Windows, Python, React, PostgreSQL)

This launcher targets the project's existing Windows installation: PostgreSQL
as a Windows service, `.venv-windows`, and Windows Node.js. Git Bash and WSL can
both launch it; the database, API, frontend, and collector all run on Windows. It does not install or
switch to a separate Linux database, Python environment, or Node installation.

## One-time preparation (Windows, Python, npm)

Complete [local PostgreSQL setup](local-postgresql.md), including the metrics
migration and private database password plus separate reader/collector tokens in
`.env`. Both tokens are required because the launcher now runs the collector.
Install updated Python dependencies from the project root in Windows PowerShell:

```powershell
.\.venv-windows\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
```

This includes `psutil` for host measurements. Install frontend dependencies from
**Windows PowerShell**:

```powershell
cd frontend
npm ci --include=optional
```

Do not share a prepared `node_modules` between Windows and Linux npm runs;
platform-specific Rollup/esbuild packages may differ. The launcher uses Windows
Node even when invoked from WSL.

Stop any FastAPI or Vite instances already running on ports 8000 and 5173.
The launcher refuses occupied ports instead of terminating existing processes.

## Start all three parts (Bash)

From the project root in **Git Bash** or **WSL with Windows interop**:

```bash
bash scripts/setup/start_local.sh
```

The launcher:

1. Checks Windows Python, Windows Node/Vite, private configuration, and free ports.
2. Finds the installed PostgreSQL Windows service and starts it if stopped.
3. Verifies the configured database login and metrics table without writing data.
4. Starts FastAPI with `.env`, local reload, and port 8000.
5. Starts the local Python collector after the API: measure, POST, sleep five
   seconds, repeat.
6. Starts React/Vite on port 5173, waits for both HTTP endpoints, and prints URLs.

Open <http://127.0.0.1:5173>, choose **Connect API**, and enter your reader token.
API documentation is at <http://127.0.0.1:8000/docs>.
The launcher doesn't send credentials to the browser or print their values.
It doesn't apply migrations, create databases, generate tokens, or install packages.

Keep the terminal open. **Ctrl+C** stops the API, frontend, and collector process
trees started by this invocation. If an app or collector exits, the launcher stops
the remaining processes and reports failure. PostgreSQL is left running because other applications may use
it; its data is preserved.

The Bash entry point uses a PowerShell helper solely for Windows service/process
management and a Python helper for sanitized configuration/storage checks.
If Bash is unavailable, run the same helper from PowerShell:

```powershell
powershell.exe -NoProfile -File .\scripts\setup\start_local_windows.ps1
```

This command does not change the system execution policy. If your local policy
blocks scripts, use your existing approved policy or the manual startup commands
in the PostgreSQL and frontend guides.

## Troubleshooting (Windows, PostgreSQL)

- **Multiple/no PostgreSQL services:** inspect names in Windows PowerShell:

  ```powershell
  Get-Service -Name 'postgresql*'
  ```

  Then select the installed name explicitly in Git Bash/WSL:

  ```bash
  bash scripts/setup/start_local.sh --postgres-service postgresql-x64-18
  ```

  Replace the example with your actual service name.
- **Stopped service cannot start:** open Windows Services (`services.msc`) and
  start PostgreSQL, granting administrator access if Windows requires it. Retry
  the launcher afterward; running the whole app as administrator is unnecessary.
- **Storage check fails:** check `.env`, database/user/password, and apply the
  migration using the local PostgreSQL guide. Errors deliberately omit secret
  values and driver details. Existing shell variables take precedence over `.env`.
- **Missing Windows Rollup/esbuild:** rerun `npm ci --include=optional` from
  Windows PowerShell inside `frontend/`.
- **Port occupied:** stop your previous API/frontend terminal with Ctrl+C.
- **WSL cannot find powershell.exe:** use Git Bash or enable Windows interop in
  your WSL configuration. Native Linux-only setups are not supported by this
  Windows-specific launcher.

## Simple local collection (Python)

The launcher now records actual CPU, memory, home-drive/filesystem disk usage,
and uptime from the Windows machine running the collector. Its core is simply:

```python
while True:
    sample = collect_sample()
    post_sample(sample, collector_token)
    time.sleep(5)
```

The actual script also handles failed requests and Ctrl+C. A short 0.1-second CPU
measurement avoids an inaccurate first nonblocking reading; see the
[psutil documentation](https://psutil.readthedocs.io/stable/).
It pauses five seconds after each attempt, so sampling takes approximately five
seconds plus measurement and request time. HTTP calls have a three-second timeout.
Failed samples are skipped; the next fresh sample is attempted after the sleep.
There is no persistent retry queue or production scheduler.

POST uses the collector token only, with a fixed loopback URL and no redirect
following. The frontend uses the reader token and polls every five seconds after
**Connect API**. A first poll can happen just before a POST, so a new measurement
may appear on the next refresh. Disk/memory values may legitimately stay the same;
uptime and the displayed latest-measurement timestamp help verify fresh samples.

If running the API manually instead of through the launcher, start just the
collector in another Windows PowerShell terminal from the project root:

```powershell
.\.venv-windows\Scripts\python.exe scripts/monitoring/collect_local.py --env-file .env
```

Do not start a second collector when the launcher is already running one. Stop
with Ctrl+C. Restart the API/collector after changing tokens in `.env`. Measurements
are real database writes that remain saved after stopping the local stack.
On EC2 the same collector runs under systemd; see [Ubuntu monitoring](ubuntu-monitoring.md).

## Verification (Bash, Python)

```bash
bash -n scripts/setup/start_local.sh
bash scripts/setup/start_local.sh --help
python -m pytest tests/test_local_launcher.py tests/test_local_collector.py -q
```

These tests cover Windows/WSL command dispatch, paths with spaces, exit status,
dummy configuration, host sampling, authenticated POST, connection cleanup,
retries, and five-second sleeps. They run in CI. Windows service startup,
process cleanup on Ctrl+C, and browser integration need a manual Windows check.
