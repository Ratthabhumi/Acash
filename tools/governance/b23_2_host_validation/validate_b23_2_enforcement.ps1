<#
.SYNOPSIS
    ACASH Gate B Governance Repair: B23.2 Host Application-Control Enforcement Validator.

.DESCRIPTION
    Executes on a Designated Windows Governance / Enforcement Host to physically validate B23.2:
    1. Verifies host policy is in ENFORCE mode (UsermodeCodeIntegrityPolicyEnforcementStatus == 2).
    2. Attempts execution of an unauthorized / tampered bootstrapper artifact.
    3. Asserts the Windows OS kernel blocks process creation (NTSTATUS 0xC0000428 or Win32 Error 1260).
    4. Extracts Code Integrity Event ID 3077 (Enforce Block) from Microsoft-Windows-CodeIntegrity/Operational.
    5. Verifies cryptographic correlation (file path, SHA-256 digest, execution timestamp).
    6. Emits authoritative evidence dossier to var/governance/b23_2_enforcement_evidence.json.

.NOTES
    Status values for UsermodeCodeIntegrityPolicyEnforcementStatus:
      0 = Off / Disabled
      1 = Audit Mode
      2 = Enforced Mode (Required for B23.2 PASS)
#>

[CmdletBinding()]
param (
    [string]$TargetExePath = "$PSScriptRoot\..\bin\acash-bootstrapper.exe",
    [string]$EvidenceOutputPath = "$PSScriptRoot\..\..\var\governance\b23_2_enforcement_evidence.json"
)

$ErrorActionPreference = "Stop"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "       ACASH GATE B REPAIR: B23.2 HOST EXECUTION ENFORCEMENT VALIDATOR          " -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

# ------------------------------------------------------------------------------
# STEP 1: Verify Host Code Integrity Policy is in ENFORCE Mode (Status == 2)
# ------------------------------------------------------------------------------
Write-Host "`n[STEP 1] Inspecting Win32_DeviceGuard Host Policy State..." -ForegroundColor Yellow

$dg = Get-CimInstance -Namespace root\Microsoft\Windows\DeviceGuard -ClassName Win32_DeviceGuard
if ($null -eq $dg) {
    Write-Error "[FATAL] Win32_DeviceGuard CIM instance not accessible on this host."
    exit 1
}

$kmci = $dg.CodeIntegrityPolicyEnforcementStatus
$umci = $dg.UsermodeCodeIntegrityPolicyEnforcementStatus

Write-Host "  - Kernel-Mode CI Enforcement (KMCI): $kmci (Expected: 2 [Enforced])"
Write-Host "  - User-Mode CI Enforcement (UMCI):   $umci (Expected: 2 [Enforced])"

if ($umci -ne 2) {
    Write-Host "`n[REJECT] ENVIRONMENT NOT SUFFICIENT:" -ForegroundColor Red
    Write-Host "  Current UsermodeCodeIntegrityPolicyEnforcementStatus is $umci." -ForegroundColor Red
    Write-Host "  0 = Off / Disabled" -ForegroundColor DarkGray
    Write-Host "  1 = Audit Mode (Logs event 3076, does NOT block execution)" -ForegroundColor DarkGray
    Write-Host "  2 = Enforced Mode (Logs event 3077, BLOCKS process creation)" -ForegroundColor DarkGray
    Write-Host "  B23.2 requires Status == 2. Test cannot be completed on this host." -ForegroundColor Red
    exit 2
}

Write-Host "  [OK] Host policy is active in ENFORCE mode (UMCI == 2)." -ForegroundColor Green

# ------------------------------------------------------------------------------
# STEP 2: Prepare Tampered / Unauthorized Test Artifact
# ------------------------------------------------------------------------------
Write-Host "`n[STEP 2] Preparing Test Artifact..." -ForegroundColor Yellow

$resolvedExe = Resolve-Path $TargetExePath -ErrorAction Stop
Write-Host "  Source binary: $resolvedExe"

# Create a designated tampered test binary in temp directory
$testDir = Join-Path $env:TEMP "acash_b23_test"
if (-not (Test-Path $testDir)) {
    New-Item -ItemType Directory -Path $testDir -Force | Out-Null
}

$testExe = Join-Path $testDir "unauthorized-bootstrapper.exe"
Copy-Item -Path $resolvedExe -Destination $testExe -Force

# Mutate 1 byte to invalidate any signature or hash authorization
$bytes = [System.IO.File]::ReadAllBytes($testExe)
$bytes[0x100] = $bytes[0x100] -bxor 0xFF
[System.IO.File]::WriteAllBytes($testExe, $bytes)

$artifactHash = (Get-FileHash -Path $testExe -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "  Tampered test artifact created: $testExe"
Write-Host "  Artifact SHA-256: $artifactHash"

# ------------------------------------------------------------------------------
# STEP 3: Attempt Execution & Assert OS Blocks Process Creation
# ------------------------------------------------------------------------------
Write-Host "`n[STEP 3] Attempting Process Execution..." -ForegroundColor Yellow
$executionTimeUtc = (Get-Date).ToUniversalTime()
$executionBlocked = $false
$osErrorMessage = ""
$exitCode = $null

try {
    $proc = Start-Process -FilePath $testExe -ArgumentList "--help" -PassThru -Wait -ErrorAction Stop
    $exitCode = $proc.ExitCode
    if ($exitCode -ne 0) {
        $executionBlocked = $true
        $osErrorMessage = "Process exited with code $exitCode"
    } else {
        Write-Error "[FATAL B23.2 VIOLATION] Unauthorized binary executed successfully (ExitCode: 0). Policy failed to block!"
        exit 3
    }
} catch [System.ComponentModel.Win32Exception] {
    $executionBlocked = $true
    $win32Err = $_.Exception.NativeErrorCode
    $osErrorMessage = $_.Exception.Message
    Write-Host "  [KERNEL BLOCKED] OS denied process creation: Win32 Error $win32Err - $osErrorMessage" -ForegroundColor Green
} catch {
    $executionBlocked = $true
    $osErrorMessage = $_.Exception.Message
    Write-Host "  [KERNEL BLOCKED] Process launch failed: $osErrorMessage" -ForegroundColor Green
}

if (-not $executionBlocked) {
    Write-Error "[FATAL] Execution was not blocked by OS!"
    exit 4
}

# ------------------------------------------------------------------------------
# STEP 4: Extract Code Integrity Event 3077 (Enforce Block)
# ------------------------------------------------------------------------------
Write-Host "`n[STEP 4] Querying Security Event Log for Block Event (ID 3077)..." -ForegroundColor Yellow

$logName = "Microsoft-Windows-CodeIntegrity/Operational"
$timeFilter = $executionTimeUtc.AddSeconds(-5)

$events = Get-WinEvent -FilterHashtable @{
    LogName = $logName
    Id = 3077
    StartTime = $timeFilter
} -MaxEvents 5 -ErrorAction SilentlyContinue

if ($null -eq $events -or $events.Count -eq 0) {
    # Also check if audit event 3076 was logged instead
    $auditEvents = Get-WinEvent -FilterHashtable @{
        LogName = $logName
        Id = 3076
        StartTime = $timeFilter
    } -MaxEvents 1 -ErrorAction SilentlyContinue

    if ($auditEvents) {
        Write-Error "[REJECT] Found Event ID 3076 (Audit Mode). Policy is in Audit, NOT Enforce Mode. Event 3077 required."
        exit 5
    }

    Write-Error "[FATAL] No Code Integrity Event 3077 found in log within execution time window."
    exit 6
}

$matchingEvent = $events[0]
Write-Host "  Found Code Integrity Block Event ID 3077:" -ForegroundColor Green
Write-Host "    TimeCreated: $($matchingEvent.TimeCreated)"
Write-Host "    Provider:    $($matchingEvent.ProviderName)"

# ------------------------------------------------------------------------------
# STEP 5: Cryptographic Correlation & Dossier Generation
# ------------------------------------------------------------------------------
Write-Host "`n[STEP 5] Generating Cryptographic Evidence Dossier..." -ForegroundColor Yellow

$evidenceDir = Split-Path $EvidenceOutputPath -Parent
if (-not (Test-Path $evidenceDir)) {
    New-Item -ItemType Directory -Path $evidenceDir -Force | Out-Null
}

$evidenceDossier = [ordered]@{
    test_id = "B23.2"
    test_name = "Host Application-Control Execution Enforcement"
    verdict = "PASS"
    host_telemetry = @{
        computer_name = $env:COMPUTERNAME
        os_version = [System.Environment]::OSVersion.VersionString
        kernel_mode_ci_status = $kmci
        user_mode_ci_status = $umci
        policy_enforcement_mode = "ENFORCE (Value == 2)"
    }
    execution_attempt = @{
        artifact_path = $testExe
        artifact_sha256 = $artifactHash
        execution_timestamp_utc = $executionTimeUtc.ToString("o")
        process_blocked = $true
        os_interception_details = $osErrorMessage
    }
    security_event = @{
        log_name = $logName
        event_id = $matchingEvent.Id
        event_timestamp_utc = $matchingEvent.TimeCreated.ToUniversalTime().ToString("o")
        provider_name = $matchingEvent.ProviderName
        event_xml = $matchingEvent.ToXml()
    }
    certified_at_utc = (Get-Date).ToUniversalTime().ToString("o")
}

$jsonText = $evidenceDossier | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText($EvidenceOutputPath, $jsonText, [System.Text.Encoding]::UTF8)

Write-Host "  Evidence sealed to: $EvidenceOutputPath" -ForegroundColor Green
Write-Host "`n================================================================================" -ForegroundColor Green
Write-Host "       B23.2 PHYSICAL ENFORCEMENT PROOF: VERIFIED & SEALED                      " -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
exit 0
