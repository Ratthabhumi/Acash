<#
.SYNOPSIS
    ACASH Phase 13 -- Step 5 Continuous 24-Hour Unattended Soak Test Launcher.

.DESCRIPTION
    Safely initiates the authorized 24-hour unattended soak test runner as an
    independent background process with strict governance preconditions:
    - Live Capital: $0.00
    - Live Orders: 0
    - Broker Wire: DISCONNECTED
    - Strategy Gating: STRAT-MOM-MULTI-HORIZON-V1 remains qualification-blocked
    - Venue: LOCAL_SIMULATOR only
    - Duration: 24.0 hours (never shortened or accelerated)

.PARAMETER PreflightOnly
    Switch to validate preconditions and display launch configuration without
    actually starting the background process.

.PARAMETER ShowHelp
    Switch to display help text.
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory = $false)]
    [switch]$PreflightOnly,

    [Parameter(Mandatory = $false)]
    [switch]$ShowHelp
)

$ErrorActionPreference = "Stop"

if ($ShowHelp) {
    Get-Help $MyInvocation.MyCommand.Path -Detailed
    exit 0
}

# 1. Resolve Repository Root Safely
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
Set-Location -Path $repoRoot

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " ACASH PHASE 13 -- STEP 5 UNATTENDED SOAK TEST LAUNCHER" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

# 2. Check Git Commit SHA
$commitSha = ""
try {
    $commitSha = (git rev-parse HEAD).Trim()
}
catch {
    Write-Error "[FAIL-CLOSED] Failed to query current Git commit SHA."
    exit 1
}

# 3. Check Virtual Environment and Runner Script
$runnerScript = Join-Path -Path $repoRoot -ChildPath "scripts\phase13_soak_runner.py"
if (-not (Test-Path -Path $runnerScript)) {
    Write-Error "[FAIL-CLOSED] Soak runner script not found at '$runnerScript'."
    exit 1
}

$uvPath = (Get-Command "uv" -ErrorAction SilentlyContinue)
if ($null -eq $uvPath) {
    Write-Error "[FAIL-CLOSED] 'uv' executable not found in PATH."
    exit 1
}

# 4. Mandatory Governance Precondition Checks
Write-Host "[CHECK] Verifying Governance Preconditions..." -ForegroundColor Yellow

$venue = "LOCAL_SIMULATOR"
$strategyId = "STRAT-MOM-MULTI-HORIZON-V1"
$strategyStatus = "QUALIFICATION_BLOCKED"
$liveCapital = "0.00"
$liveOrders = 0
$brokerWire = "DISCONNECTED"
$durationHours = 24.0
$pulseIntervalSec = 1.0
$telemetryIntervalSec = 10.0
$outputDirRel = "var/phase13_soak"
$outputDirAbs = Join-Path -Path $repoRoot -ChildPath "var\phase13_soak"

Write-Host ("  -> Venue                  : " + $venue) -ForegroundColor Gray
Write-Host ("  -> Strategy               : " + $strategyId + " (" + $strategyStatus + ")") -ForegroundColor Gray
Write-Host ("  -> Live Capital Authority : `$" + $liveCapital) -ForegroundColor Gray
Write-Host ("  -> Live Orders Allowed    : " + $liveOrders) -ForegroundColor Gray
Write-Host ("  -> Broker Wire            : " + $brokerWire) -ForegroundColor Gray
Write-Host ("  -> Duration Target        : " + $durationHours + " Hours (Continuous Unattended)") -ForegroundColor Gray
Write-Host ("  -> Output Directory       : " + $outputDirAbs) -ForegroundColor Gray

# 5. Check Output Directory and Existing Process
if (-not (Test-Path -Path $outputDirAbs)) {
    New-Item -ItemType Directory -Path $outputDirAbs -Force | Out-Null
}

$pidFile = Join-Path -Path $outputDirAbs -ChildPath "soak_runner.pid"
if (Test-Path -Path $pidFile) {
    $existingPidRaw = (Get-Content -Path $pidFile -Raw).Trim()
    if ($existingPidRaw -match "^\d+$") {
        $existingPid = [int]$existingPidRaw
        $existingProc = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
        if ($null -ne $existingProc) {
            Write-Error "[FAIL-CLOSED] A soak runner process is ALREADY RUNNING with PID $existingPid."
            exit 1
        }
    }
}

# 6. Archive Stale Run Artifacts from Inactive/Aborted Previous Runs
if (-not $PreflightOnly) {
    $archiveDirRoot = Join-Path -Path $outputDirAbs -ChildPath "archive"
    $staleItems = Get-ChildItem -Path $outputDirAbs -Exclude "archive" -ErrorAction SilentlyContinue
    if ($null -ne $staleItems -and $staleItems.Count -gt 0) {
        $archiveTime = (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss")
        $archiveDir = Join-Path -Path $archiveDirRoot -ChildPath ("aborted_" + $archiveTime)
        New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null
        foreach ($item in $staleItems) {
            Move-Item -Path $item.FullName -Destination $archiveDir -Force
        }
        Write-Host ("[MAINT] Cleaned previous run artifacts (archived to: " + $archiveDir + ")") -ForegroundColor Yellow
    }
}

# 7. Locate Python Executable in Virtual Environment
$pythonw = Join-Path -Path $repoRoot -ChildPath ".venv\Scripts\pythonw.exe"
if (-not (Test-Path -Path $pythonw)) {
    $pythonw = Join-Path -Path $repoRoot -ChildPath ".venv\Scripts\python.exe"
}
if (-not (Test-Path -Path $pythonw)) {
    Write-Error "[FAIL-CLOSED] Python executable not found in virtual environment (.venv)."
    exit 1
}

# 8. Construct Command Arguments
$argList = @(
    "-u",
    $runnerScript,
    "--duration-hours", "24.0",
    "--pulse-interval-sec", "1.0",
    "--telemetry-interval-sec", "10.0",
    "--output-dir", "var/phase13_soak",
    "--venue", "LOCAL_SIMULATOR"
)
$exactCmd = "$pythonw -u scripts/phase13_soak_runner.py --duration-hours 24.0 --pulse-interval-sec 1.0 --telemetry-interval-sec 10.0 --output-dir var/phase13_soak --venue LOCAL_SIMULATOR"

# 9. Handle PreflightOnly Switch
if ($PreflightOnly) {
    Write-Host ""
    Write-Host "[PREFLIGHT SUCCESS] All preconditions satisfied. Launcher is ready." -ForegroundColor Green
    Write-Host ("  -> Commit SHA      : " + $commitSha)
    Write-Host ("  -> Constructed Cmd : " + $exactCmd)
    Write-Host "  -> PreflightOnly flag supplied. Process NOT spawned." -ForegroundColor Yellow
    exit 0
}

# 10. Launch Background Process using Splatting
Write-Host ""
Write-Host "[LAUNCH] Spawning background 24-hour soak daemon..." -ForegroundColor Cyan
$launchTimeUtc = (Get-Date).ToUniversalTime().ToString("o")

$stdoutPath = Join-Path -Path $outputDirAbs -ChildPath "soak_stdout.log"
$stderrPath = Join-Path -Path $outputDirAbs -ChildPath "soak_stderr.log"

$processParams = @{
    FilePath               = $pythonw
    ArgumentList           = $argList
    WorkingDirectory       = $repoRoot
    RedirectStandardOutput = $stdoutPath
    RedirectStandardError  = $stderrPath
    PassThru               = $true
}

$process = Start-Process @processParams

# Brief pause to verify startup stability
Start-Sleep -Milliseconds 500

if ($null -eq $process -or $process.HasExited) {
    $errDetail = ""
    if (Test-Path -Path $stderrPath) {
        $errDetail = (Get-Content -Path $stderrPath -Raw).Trim()
    }
    Write-Error "[FAIL-CLOSED] Failed to start soak runner background process. $errDetail"
    exit 1
}

$soakPid = $process.Id
Set-Content -Path $pidFile -Value $soakPid -Force


# 11. Record Launch Metadata
$launchMetadata = [ordered]@{
    "pid"                     = $soakPid
    "launch_timestamp_utc"    = $launchTimeUtc
    "commit_sha"              = $commitSha
    "venue"                   = $venue
    "duration_hours"          = $durationHours
    "pulse_interval_sec"      = $pulseIntervalSec
    "telemetry_interval_sec"  = $telemetryIntervalSec
    "output_dir"              = "var/phase13_soak"
    "exact_command"           = $exactCmd
    "strategy_id"             = $strategyId
    "strategy_status"         = $strategyStatus
    "live_capital_usd"        = $liveCapital
    "live_orders"             = $liveOrders
    "broker_wire"             = $brokerWire
    "step5_governance_status" = "RUNNING_NOT_YET_PASSED"
}
$metadataPath = Join-Path -Path $outputDirAbs -ChildPath "soak_launch.json"
$launchMetadata | ConvertTo-Json -Depth 4 | Set-Content -Path $metadataPath -Force

# 12. Display Confirmation and Monitoring Guidance
Write-Host "================================================================================" -ForegroundColor Green
Write-Host " ACASH PHASE 13 -- STEP 5 SOAK RUNNER ACTIVATED" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
Write-Host ("  Process PID          : " + $soakPid) -ForegroundColor White
Write-Host ("  Commit SHA           : " + $commitSha) -ForegroundColor White
Write-Host ("  Launch UTC           : " + $launchTimeUtc) -ForegroundColor White
Write-Host ("  Planned Duration     : 24.0 Hours") -ForegroundColor White
Write-Host ("  Output Directory     : " + $outputDirAbs) -ForegroundColor White
Write-Host ("  Telemetry Log        : " + $outputDirAbs + "\soak_telemetry.jsonl") -ForegroundColor White
Write-Host ("  Process Stdout Log   : " + $stdoutPath) -ForegroundColor White
Write-Host ("  PID File             : " + $pidFile) -ForegroundColor White
Write-Host ("  Launch Metadata      : " + $metadataPath) -ForegroundColor White
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor Gray
Write-Host "  GOVERNANCE STATUS    : STEP 5 IS NOW RUNNING -- NOT YET PASSED" -ForegroundColor Yellow
Write-Host "  MONITORING COMMAND   : powershell -File .\scripts\status_phase13_soak.ps1" -ForegroundColor Cyan
Write-Host ("  LIVE TAIL COMMAND    : Get-Content -Tail 20 -Wait " + $outputDirAbs + "\soak_telemetry.jsonl") -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Green
