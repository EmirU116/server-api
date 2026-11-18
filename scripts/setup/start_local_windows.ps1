<#
Windows service/process control for the Bash entry point. Secrets stay in .env;
neither this controller nor the frontend receives database or collector values
from that file. PostgreSQL is reused and is never stopped during cleanup.
#>
[CmdletBinding()]
param([string]$PostgresService = "")

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$projectDir = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$python = Join-Path $projectDir ".venv-windows/Scripts/python.exe"
$frontendDir = Join-Path $projectDir "frontend"
$vite = Join-Path $frontendDir "node_modules/vite/bin/vite.js"
$checker = Join-Path $PSScriptRoot "check_local.py"
$apiProcess = $null
$frontendProcess = $null

function Assert-PortFree([int]$Port) {
    $listener = [System.Net.Sockets.TcpListener]::new(
        [System.Net.IPAddress]::Parse("127.0.0.1"), $Port
    )
    try {
        $listener.Start()
    } catch {
        throw "Port $Port is occupied. Stop the existing local app before launching."
    } finally {
        $listener.Stop()
    }
}

function Wait-Http([string]$Url, [int]$ExpectedStatus, $Process) {
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if ($Process.HasExited) {
            throw "A local application exited before it became ready. Check its output above."
        }
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 1
            if ([int]$response.StatusCode -eq $ExpectedStatus) { return }
        } catch {
            $responseProperty = $_.Exception.PSObject.Properties["Response"]
            if ($null -ne $responseProperty -and $null -ne $responseProperty.Value) {
                if ([int]$responseProperty.Value.StatusCode -eq $ExpectedStatus) { return }
            }
        }
        Start-Sleep -Milliseconds 500
    }
    throw "A local application did not become ready in time. Check its output above."
}

function Stop-OwnedProcess($Process) {
    if ($null -ne $Process -and -not $Process.HasExited) {
        # Target only process trees created by this invocation, including reload
        # workers. Never kill every python/node process or an occupied-port owner.
        try {
            & taskkill.exe /PID $Process.Id /T /F 2>$null | Out-Null
        } catch {
            Write-Host "WARN: Could not finish app cleanup; check the local app processes."
        }
    }
}

Push-Location $projectDir
try {
    if (-not (Test-Path -LiteralPath $python)) {
        throw "Missing Windows virtual environment. Follow docs/local-postgresql.md."
    }
    if (-not (Test-Path -LiteralPath (Join-Path $projectDir ".env"))) {
        throw "Missing private .env. Follow docs/local-postgresql.md."
    }
    if (-not (Test-Path -LiteralPath $vite)) {
        throw "Missing frontend dependencies. Run npm ci --include=optional in frontend using Windows PowerShell."
    }
    $node = (Get-Command node.exe -ErrorAction Stop).Source
    # Loading Vite catches missing Windows Rollup/esbuild binaries before any
    # service or app is started. Do not repair dependencies from WSL here.
    & $node $vite --version
    if ($LASTEXITCODE -ne 0) {
        throw "Vite cannot start. Run npm ci --include=optional in frontend using Windows PowerShell."
    }
    & $python $checker --configuration-only
    if ($LASTEXITCODE -ne 0) { throw "Fix local configuration before starting services." }
    Assert-PortFree 8000
    Assert-PortFree 5173

    if ($PostgresService) {
        $services = @(Get-Service -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq $PostgresService })
    } else {
        $services = @(Get-Service -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "postgresql*" })
    }
    if ($services.Count -ne 1) {
        throw "Expected one PostgreSQL service. Use --postgres-service NAME to select yours."
    }
    $databaseService = $services[0]
    if ($databaseService.Status -ne "Running") {
        try {
            Start-Service -InputObject $databaseService
            $databaseService.WaitForStatus("Running", [TimeSpan]::FromSeconds(20))
        } catch {
            throw "Cannot start PostgreSQL. Start it in Windows Services (services.msc), then retry. Administrator rights may be required."
        }
    }
    Write-Host "PASS: PostgreSQL service is running ($($databaseService.Name))."
    & $python $checker
    if ($LASTEXITCODE -ne 0) { throw "Fix database access or run the metrics migration before launching." }

    $apiProcess = Start-Process -FilePath $python -WorkingDirectory $projectDir `
        -ArgumentList '-m uvicorn app.main:create_app --factory --app-dir backend --env-file .env --reload --host 127.0.0.1 --port 8000' `
        -NoNewWindow -PassThru
    # Invalid ID always returns 400; this readiness check works for any configured
    # server ID and does not require or expose an authentication token.
    Wait-Http "http://127.0.0.1:8000/api/v1/health?server_id=0" 400 $apiProcess
    Write-Host "PASS: FastAPI is ready."

    $frontendProcess = Start-Process -FilePath $node -WorkingDirectory $frontendDir `
        -ArgumentList ('"' + $vite + '" --host 127.0.0.1 --port 5173 --strictPort') `
        -NoNewWindow -PassThru
    Wait-Http "http://127.0.0.1:5173" 200 $frontendProcess
    Write-Host "PASS: React is ready."
    Write-Host "Frontend: http://127.0.0.1:5173"
    Write-Host "API docs: http://127.0.0.1:8000/docs"
    Write-Host "Choose Connect API in the dashboard and use your private reader token."
    Write-Host "Press Ctrl+C to stop React and FastAPI. PostgreSQL stays running."

    while (-not $apiProcess.HasExited -and -not $frontendProcess.HasExited) {
        Start-Sleep -Seconds 1
    }
    throw "A local application exited. Stopping the other application."
} catch {
    Write-Host "FAIL: $($_.Exception.Message)"
    exit 1
} finally {
    Stop-OwnedProcess $frontendProcess
    Stop-OwnedProcess $apiProcess
    Pop-Location
}
