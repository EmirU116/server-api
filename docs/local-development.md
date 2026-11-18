# Start the local stack (Bash, Windows, Python, React, PostgreSQL)

This launcher targets the project's existing Windows installation: PostgreSQL
as a Windows service, `.venv-windows`, and Windows Node.js. Git Bash and WSL can
both launch it; all three services still run on Windows. It does not install or
switch to a separate Linux database, Python environment, or Node installation.

## One-time preparation (Windows, Python, npm)

Complete [local PostgreSQL setup](local-postgresql.md), including the metrics
migration and private database password/reader token in `.env`. A collector token
is needed only for submitting measurements, not starting the dashboard.
Install frontend dependencies from **Windows PowerShell**:

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
5. Starts React/Vite on port 5173, waits for both HTTP endpoints, and prints URLs.

Open <http://127.0.0.1:5173>, choose **Connect API**, and enter your reader token.
API documentation is at <http://127.0.0.1:8000/docs>.
The launcher doesn't send credentials to the browser or print their values.
It doesn't apply migrations, create databases, generate tokens, or install packages.

Keep the terminal open. **Ctrl+C** stops the API/frontend process trees started
by this invocation. If either app exits, the launcher stops the other one and
reports failure. PostgreSQL is left running because other applications may use
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

This starts existing components. Automatic metric collection and periodic UI
refresh remain separate work; starting the stack does not generate measurements.

## Verification (Bash, Python)

```bash
bash -n scripts/setup/start_local.sh
bash scripts/setup/start_local.sh --help
python -m pytest tests/test_local_launcher.py -q
```

The 14 launcher tests passed, covering Windows/WSL command dispatch, paths with
spaces, exit status propagation, input errors, and dummy configuration checks.
The three existing EC2 verification tests also passed. Bash syntax/help and
Python lint/format checks passed. ShellCheck was unavailable. Actual Windows service startup, process
cleanup on Ctrl+C, and browser integration require a Windows smoke test; they
have not been verified in the Linux development environment.
