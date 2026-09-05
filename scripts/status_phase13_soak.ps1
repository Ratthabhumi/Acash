<#
.SYNOPSIS
    ACASH Phase 13 -- Step 5 Continuous Soak Test Status and Observability Monitor.

.DESCRIPTION
    Non-mutating companion script inspecting the active state of the 24-hour
    unattended soak test:
    - Checks if the recorded PID is alive
    - Inspects process memory and CPU utilization
    - Reads line count and latest record from soak_telemetry.jsonl
    - Inspects final summary if execution has concluded
    - Strictly OBSERVABILITY ONLY: Never modifies runtime state.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# 1. Resolve Repository Root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
Set-Location -Path $repoRoot

$outputDirAbs = Join-Path -Path $repoRoot -ChildPath "var\phase13_soak"
$pidFile = Join-Path -Path $outputDirAbs -ChildPath "soak_runner.pid"
$launchFile = Join-Path -Path $outputDirAbs -ChildPath "soak_launch.json"
$telemetryFile = Join-Path -Path $outputDirAbs -ChildPath "soak_telemetry.jsonl"
$summaryFile = Join-Path -Path $outputDirAbs -ChildPath "soak_summary.json"
$stderrFile = Join-Path -Path $outputDirAbs -ChildPath "soak_stderr.log"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " ACASH PHASE 13 -- STEP 5 SOAK RUNNER STATUS MONITOR" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

if (-not (Test-Path -Path $outputDirAbs)) {
    Write-Host "[STATUS] Output directory does not exist yet:" -ForegroundColor Yellow
    Write-Host ("         " + $outputDirAbs) -ForegroundColor Yellow
    Write-Host "         The 24-hour soak test has not been launched." -ForegroundColor Yellow
    exit 0
}

# 2. Check Launch Metadata
if (Test-Path -Path $launchFile) {
    try {
        $launchMeta = Get-Content -Path $launchFile -Raw | ConvertFrom-Json
        Write-Host "Launch Metadata:" -ForegroundColor Gray
        Write-Host ("  -> Launch Time UTC : " + $launchMeta.launch_timestamp_utc)
        Write-Host ("  -> Commit SHA      : " + $launchMeta.commit_sha)
        Write-Host ("  -> Venue           : " + $launchMeta.venue)
        Write-Host ("  -> Planned Duration: " + $launchMeta.duration_hours + " Hours")
    }
    catch {
        Write-Warning "Failed to parse soak_launch.json."
    }
}

# 3. Check Process PID
$pidRunning = $false
$soakProc = $null
$soakPid = $null

if (Test-Path -Path $pidFile) {
    $pidRaw = (Get-Content -Path $pidFile -Raw).Trim()
    if ($pidRaw -match "^\d+$") {
        $soakPid = [int]$pidRaw
        $soakProc = Get-Process -Id $soakPid -ErrorAction SilentlyContinue
        if ($null -ne $soakProc) {
            $pidRunning = $true
        }
    }
}

Write-Host ""
if ($pidRunning -and ($null -ne $soakProc)) {
    $rssMb = [math]::Round($soakProc.WorkingSet64 / 1MB, 2)
    $cpuSec = [math]::Round($soakProc.TotalProcessorTime.TotalSeconds, 2)
    Write-Host "PROCESS STATUS: ACTIVE / RUNNING" -ForegroundColor Green
    Write-Host ("  PID                : " + $soakPid)
    Write-Host ("  Process Name       : " + $soakProc.ProcessName)
    Write-Host ("  Working Set (RSS)  : " + $rssMb + " MB")
    Write-Host ("  CPU Time (sec)     : " + $cpuSec)
    Write-Host ("  Start Time (Local) : " + $soakProc.StartTime)
} else {
    Write-Host "PROCESS STATUS: INACTIVE / NOT RUNNING" -ForegroundColor Yellow
    if ($null -ne $soakPid) {
        Write-Host ("  Recorded PID       : " + $soakPid + " (Process not found in active process table)")
    }
}

# 4. Check Telemetry File
Write-Host ""
if (Test-Path -Path $telemetryFile) {
    $lineCount = (Get-Content -Path $telemetryFile | Measure-Object -Line).Lines
    Write-Host "Telemetry Log:" -ForegroundColor Gray
    Write-Host ("  File               : " + $telemetryFile)
    Write-Host ("  Samples Recorded   : " + $lineCount)

    if ($lineCount -gt 0) {
        $lastLine = Get-Content -Path $telemetryFile -Tail 1
        try {
            $latest = $lastLine | ConvertFrom-Json
            $elapsedH = [math]::Round($latest.elapsed_seconds / 3600.0, 2)
            Write-Host "Latest Telemetry Sample:" -ForegroundColor Cyan
            Write-Host ("  Timestamp UTC      : " + $latest.timestamp_utc)
            Write-Host ("  Elapsed            : " + $latest.elapsed_seconds + "s (" + $elapsedH + "h)")
            Write-Host ("  Pulses Executed    : " + $latest.pulse_count)
            Write-Host ("  Process RSS        : " + $latest.rss_mb + " MB (Peak: " + $latest.peak_rss_mb + " MB)")
            Write-Host ("  Ledger Events      : " + $latest.ledger_event_count)
            Write-Host ("  Runtime Health     : " + $latest.runtime_health)
        }
        catch {
            Write-Warning "Could not parse latest telemetry line."
        }
    }
} else {
    Write-Host "Telemetry Log: NOT FOUND" -ForegroundColor Yellow
}

# 5. Check Summary File
Write-Host ""
if (Test-Path -Path $summaryFile) {
    Write-Host "FINAL SUMMARY AVAILABLE:" -ForegroundColor Green
    try {
        $summary = Get-Content -Path $summaryFile -Raw | ConvertFrom-Json
        Write-Host ("  Soak Status        : " + $summary.soak_status) -ForegroundColor White
        Write-Host ("  Total Uptime       : " + $summary.total_uptime_seconds + "s (" + $summary.total_uptime_hours + "h)")
        Write-Host ("  Pulses Executed    : " + $summary.pulses_executed)
        Write-Host ("  Memory Growth      : " + $summary.memory_growth_mb + " MB (Peak: " + $summary.peak_rss_mb + " MB)")
        Write-Host ("  Exceptions Count   : " + $summary.exceptions_count)
        Write-Host ("  Ledger Valid       : " + $summary.ledger_valid)
        Write-Host ("  Ledger Events      : " + $summary.ledger_event_count)
        Write-Host ("  Strategy Gated     : " + $summary.strategy_id + " (Blocked: " + $summary.strategy_qualification_blocked + ")")

        if (($summary.total_uptime_hours -ge 24.0) -and ($summary.exceptions_count -eq 0) -and ($summary.ledger_valid -eq $true)) {
            Write-Host ""
            Write-Host ">> 24-HOUR MINIMUM WINDOW SATISFIED -- READY FOR STEP 6 AUDIT <<" -ForegroundColor Green
        } else {
            Write-Host ""
            Write-Host ">> SOAK CONCLUDED BEFORE 24 HOURS OR WITH EXCEPTIONS <<" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Warning "Failed to parse soak_summary.json."
    }
} else {
    if ($pidRunning) {
        Write-Host "Final Summary: PENDING (Process is actively running)" -ForegroundColor Gray
    } else {
        Write-Host "Final Summary: NOT GENERATED" -ForegroundColor Yellow
        if (Test-Path -Path $stderrFile) {
            $errContent = Get-Content -Path $stderrFile -Raw
            if (-not [string]::IsNullOrWhiteSpace($errContent)) {
                Write-Host "Stderr Output from Process:" -ForegroundColor Red
                Write-Host $errContent -ForegroundColor Red
            }
        }
    }
}
Write-Host "================================================================================" -ForegroundColor Cyan
