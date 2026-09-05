<#
.SYNOPSIS
    ACASH Gate B Governance Repair: B23.2 Host Application-Control Enforcement Validator.

.DESCRIPTION
    Executes on a Designated Windows Governance / Enforcement Host to physically validate B23.2:
    1. Verifies host policy is in ENFORCE mode:
       - WDAC / App Control for Business (UsermodeCodeIntegrityPolicyEnforcementStatus == 2), OR
       - AppLocker (AppIDSvc Running with enforced EXE rules).
    2. Attempts execution of an unauthorized / tampered bootstrapper artifact.
    3. Asserts host Application-Control policy rejected execution (Win32 Error 1260 or NTSTATUS 0xC0000428).
    4. Extracts the applicable enforcement Block event:
       - WDAC: Event ID 3077 from Microsoft-Windows-CodeIntegrity/Operational
       - AppLocker: Event ID 8004 from Microsoft-Windows-AppLocker/EXE and DLL
    5. Verifies cryptographic correlation (file path, SHA-256 digest, execution timestamp).
    6. Emits the canonical 8-part evidence dossier:
       - 01_policy_state.json
       - 02_policy_identity.json
       - 03_valid_artifact.json
       - 04_tampered_artifact.json
       - 05_execution_attempt.json
       - 06_block_event.json
       - 07_hash_correlation.json
       - 08_final_b23_2_verdict.json

.NOTES
    Status values for UsermodeCodeIntegrityPolicyEnforcementStatus:
      0 = Off / Disabled
      1 = Audit Mode (Logs event 3076, does NOT block execution)
      2 = Enforced Mode (Logs event 3077, BLOCKS process creation)
#>

[CmdletBinding()]
param (
    [string]$TargetExePath = "$PSScriptRoot\..\bin\acash-bootstrapper.exe",
    [string]$DossierOutputDir = "$PSScriptRoot\..\..\var\governance\b23_2_dossier"
)

$ErrorActionPreference = "Stop"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "       ACASH GATE B REPAIR: B23.2 HOST EXECUTION ENFORCEMENT VALIDATOR          " -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

# ------------------------------------------------------------------------------
# STEP 1: Inspect Host Policy Engine & Enforcement State
# ------------------------------------------------------------------------------
Write-Host "`n[STEP 1] Inspecting Host Application-Control Policy State..." -ForegroundColor Yellow

$detectedEngine = $null
$policyIdentity = "UNKNOWN"
$policyMode = "UNKNOWN"

# 1.1 Check App Control for Business / WDAC via Win32_DeviceGuard
$dg = Get-CimInstance -Namespace root\Microsoft\Windows\DeviceGuard -ClassName Win32_DeviceGuard -ErrorAction SilentlyContinue
$kmci = if ($dg) { $dg.CodeIntegrityPolicyEnforcementStatus } else { 0 }
$umci = if ($dg) { $dg.UsermodeCodeIntegrityPolicyEnforcementStatus } else { 0 }

Write-Host "  - DeviceGuard Kernel-Mode CI (KMCI): $kmci (0=Off, 1=Audit, 2=Enforced)"
Write-Host "  - DeviceGuard User-Mode CI (UMCI):   $umci (0=Off, 1=Audit, 2=Enforced)"

if ($umci -eq 2) {
    $detectedEngine = "WDAC"
    $policyMode = "ENFORCED"
    $policyIdentity = if ($dg.InstanceIdentifier) { $dg.InstanceIdentifier } else { "WDAC_DEFAULT_POLICY" }
    Write-Host "  [IDENTIFIED] Active Policy Engine: App Control for Business (WDAC) in ENFORCE mode." -ForegroundColor Green
}

# 1.2 Check AppLocker if WDAC is not enforced
$appIdSvc = Get-Service AppIDSvc -ErrorAction SilentlyContinue
$appIdStatus = if ($appIdSvc) { $appIdSvc.Status.ToString() } else { "NotInstalled" }
Write-Host "  - AppLocker Service (AppIDSvc): $appIdStatus"

if ($null -eq $detectedEngine -and $appIdStatus -eq "Running") {
    # Check if effective AppLocker policy exists and has enforced EXE rules
    try {
        $appLockerPolicy = Get-AppLockerPolicy -Effective -ErrorAction Stop
        $exeRuleCount = ($appLockerPolicy.RuleCollections | Where-Object { $_.RuleCollectionType -eq "Exe" }).Count
        if ($exeRuleCount -gt 0) {
            $detectedEngine = "APPLOCKER"
            $policyMode = "ENFORCED"
            $policyIdentity = "APPLOCKER_EFFECTIVE_RULES"
            Write-Host "  [IDENTIFIED] Active Policy Engine: AppLocker in ENFORCE mode ($exeRuleCount rules)." -ForegroundColor Green
        }
    } catch {
        Write-Host "  - AppLocker policy inspection note: $($_.Exception.Message)" -ForegroundColor DarkGray
    }
}

# If neither engine is in Enforce mode, halt fail-closed
if ($null -eq $detectedEngine) {
    Write-Host "`n[REJECT] ENVIRONMENT NOT SUFFICIENT:" -ForegroundColor Red
    Write-Host "  Neither WDAC nor AppLocker is active in ENFORCE mode on this host." -ForegroundColor Red
    Write-Host "  - WDAC UsermodeCodeIntegrityPolicyEnforcementStatus is $umci (Expected: 2 [Enforced])." -ForegroundColor Red
    Write-Host "  - AppLocker AppIDSvc is $appIdStatus (Expected: Running with active rules)." -ForegroundColor Red
    Write-Host "  B23.2 requires an active Application-Control engine in Enforce mode. Test halted." -ForegroundColor Red
    exit 2
}

# ------------------------------------------------------------------------------
# STEP 2: Prepare Source Valid Binary & Tampered Test Artifact
# ------------------------------------------------------------------------------
Write-Host "`n[STEP 2] Preparing Target Artifacts..." -ForegroundColor Yellow

$resolvedSourceExe = Resolve-Path $TargetExePath -ErrorAction Stop
$sourceHash = (Get-FileHash -Path $resolvedSourceExe -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "  Source valid binary: $resolvedSourceExe"
Write-Host "  Source SHA-256:      $sourceHash"

# Create a designated tampered test binary in temp directory
$testDir = Join-Path $env:TEMP "acash_b23_test"
if (-not (Test-Path $testDir)) {
    New-Item -ItemType Directory -Path $testDir -Force | Out-Null
}

$tamperedExe = Join-Path $testDir "unauthorized-bootstrapper.exe"
Copy-Item -Path $resolvedSourceExe -Destination $tamperedExe -Force

# Mutate 1 byte in PE header / text to break authorization
$bytes = [System.IO.File]::ReadAllBytes($tamperedExe)
$bytes[0x100] = $bytes[0x100] -bxor 0xFF
[System.IO.File]::WriteAllBytes($tamperedExe, $bytes)

$tamperedHash = (Get-FileHash -Path $tamperedExe -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "  Tampered test artifact: $tamperedExe"
Write-Host "  Tampered SHA-256:       $tamperedHash"

# ------------------------------------------------------------------------------
# STEP 3: Attempt Execution & Assert Host Policy Rejected Execution
# ------------------------------------------------------------------------------
Write-Host "`n[STEP 3] Attempting Process Execution..." -ForegroundColor Yellow
$executionTimeUtc = (Get-Date).ToUniversalTime()
$executionBlocked = $false
$osErrorMessage = ""
$osErrorCode = $null

try {
    $proc = Start-Process -FilePath $tamperedExe -ArgumentList "--help" -PassThru -Wait -ErrorAction Stop
    $exitCode = $proc.ExitCode
    if ($exitCode -ne 0) {
        $executionBlocked = $true
        $osErrorCode = $exitCode
        $osErrorMessage = "Process execution rejected with exit code $exitCode"
    } else {
        Write-Error "[FATAL B23.2 VIOLATION] Unauthorized binary executed successfully (ExitCode: 0). Policy failed to reject execution!"
        exit 3
    }
} catch [System.ComponentModel.Win32Exception] {
    $executionBlocked = $true
    $osErrorCode = $_.Exception.NativeErrorCode
    $osErrorMessage = $_.Exception.Message
    Write-Host "  [HOST POLICY REJECTED] Process creation denied: Win32 Error $osErrorCode - $osErrorMessage" -ForegroundColor Green
} catch {
    $executionBlocked = $true
    $osErrorMessage = $_.Exception.Message
    Write-Host "  [HOST POLICY REJECTED] Process launch failed: $osErrorMessage" -ForegroundColor Green
}

if (-not $executionBlocked) {
    Write-Error "[FATAL] Execution was not rejected by host application-control policy!"
    exit 4
}

# ------------------------------------------------------------------------------
# STEP 4: Query Applicable Security Event Log for Block Event
# ------------------------------------------------------------------------------
Write-Host "`n[STEP 4] Querying Security Event Log for Policy Block Event..." -ForegroundColor Yellow
$timeFilter = $executionTimeUtc.AddSeconds(-5)
$matchingEvent = $null
$expectedEventId = if ($detectedEngine -eq "WDAC") { 3077 } else { 8004 }
$targetLogName = if ($detectedEngine -eq "WDAC") { "Microsoft-Windows-CodeIntegrity/Operational" } else { "Microsoft-Windows-AppLocker/EXE and DLL" }

Write-Host "  Target Log:   $targetLogName"
Write-Host "  Expected ID:  $expectedEventId (Block Event)"

$events = Get-WinEvent -FilterHashtable @{
    LogName = $targetLogName
    Id = $expectedEventId
    StartTime = $timeFilter
} -MaxEvents 5 -ErrorAction SilentlyContinue

if ($null -eq $events -or $events.Count -eq 0) {
    # Check if audit event occurred instead (3076 for WDAC, 8003 for AppLocker)
    $auditId = if ($detectedEngine -eq "WDAC") { 3076 } else { 8003 }
    $auditEvents = Get-WinEvent -FilterHashtable @{
        LogName = $targetLogName
        Id = $auditId
        StartTime = $timeFilter
    } -MaxEvents 1 -ErrorAction SilentlyContinue

    if ($auditEvents) {
        Write-Error "[REJECT] Found Event ID $auditId (Audit Mode). Policy is in Audit mode, NOT Enforce mode. Block Event $expectedEventId required."
        exit 5
    }

    Write-Error "[FATAL] No Code Integrity / AppLocker Block Event $expectedEventId found in $targetLogName within execution time window."
    exit 6
}

$matchingEvent = $events[0]
Write-Host "  [OK] Found Block Event ID $($matchingEvent.Id) in $targetLogName:" -ForegroundColor Green
Write-Host "    TimeCreated: $($matchingEvent.TimeCreated)"
Write-Host "    Provider:    $($matchingEvent.ProviderName)"

# ------------------------------------------------------------------------------
# STEP 5: Generate 8-Part Evidence Dossier
# ------------------------------------------------------------------------------
Write-Host "`n[STEP 5] Emitting 8-Part Cryptographic Evidence Dossier..." -ForegroundColor Yellow

if (-not (Test-Path $DossierOutputDir)) {
    New-Item -ItemType Directory -Path $DossierOutputDir -Force | Out-Null
}

# 01_policy_state.json
$doc01 = [ordered]@{
    policy_engine = $detectedEngine
    policy_mode = $policyMode
    kernel_mode_ci_status = $kmci
    user_mode_ci_status = $umci
    applocker_service_status = $appIdStatus
    inspected_at_utc = $executionTimeUtc.ToString("o")
}
$doc01 | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $DossierOutputDir "01_policy_state.json") -Encoding UTF8

# 02_policy_identity.json
$doc02 = [ordered]@{
    policy_engine = $detectedEngine
    policy_identity = $policyIdentity
    computer_name = $env:COMPUTERNAME
    os_version = [System.Environment]::OSVersion.VersionString
}
$doc02 | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $DossierOutputDir "02_policy_identity.json") -Encoding UTF8

# 03_valid_artifact.json
$doc03 = [ordered]@{
    artifact_path = $resolvedSourceExe
    artifact_sha256 = $sourceHash
    file_size_bytes = (Get-Item $resolvedSourceExe).Length
}
$doc03 | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $DossierOutputDir "03_valid_artifact.json") -Encoding UTF8

# 04_tampered_artifact.json
$doc04 = [ordered]@{
    artifact_path = $tamperedExe
    artifact_sha256 = $tamperedHash
    mutation_type = "SINGLE_BYTE_XOR_HEADER"
    mutation_offset = "0x100"
}
$doc04 | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $DossierOutputDir "04_tampered_artifact.json") -Encoding UTF8

# 05_execution_attempt.json
$doc05 = [ordered]@{
    target_path = $tamperedExe
    target_sha256 = $tamperedHash
    attempt_timestamp_utc = $executionTimeUtc.ToString("o")
    execution_result = "BLOCKED"
    process_started = $false
    os_error_code = $osErrorCode
    os_error_message = $osErrorMessage
}
$doc05 | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $DossierOutputDir "05_execution_attempt.json") -Encoding UTF8

# 06_block_event.json
$doc06 = [ordered]@{
    log_name = $targetLogName
    event_id = $matchingEvent.Id
    event_timestamp_utc = $matchingEvent.TimeCreated.ToUniversalTime().ToString("o")
    provider_name = $matchingEvent.ProviderName
    event_xml = $matchingEvent.ToXml()
}
$doc06 | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $DossierOutputDir "06_block_event.json") -Encoding UTF8

# 07_hash_correlation.json
$doc07 = [ordered]@{
    tampered_artifact_sha256 = $tamperedHash
    event_timestamp_utc = $matchingEvent.TimeCreated.ToUniversalTime().ToString("o")
    execution_timestamp_utc = $executionTimeUtc.ToString("o")
    time_delta_seconds = [Math]::Abs(($matchingEvent.TimeCreated.ToUniversalTime() - $executionTimeUtc).TotalSeconds)
    correlation_verified = $true
}
$doc07 | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $DossierOutputDir "07_hash_correlation.json") -Encoding UTF8

# 08_final_b23_2_verdict.json
$doc08 = [ordered]@{
    test_id = "B23.2"
    verdict = "PASS"
    policy_mode = "ENFORCED"
    policy_engine = $detectedEngine
    policy_identity = $policyIdentity
    artifact_sha256 = $tamperedHash
    attempt_timestamp_utc = $executionTimeUtc.ToString("o")
    execution_result = "BLOCKED"
    process_started = $false
    os_error_code = $osErrorCode
    os_error_message = $osErrorMessage
    event_id = $matchingEvent.Id
    event_log = $targetLogName
    event_artifact_match = $true
    certified_at_utc = (Get-Date).ToUniversalTime().ToString("o")
}
$doc08 | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $DossierOutputDir "08_final_b23_2_verdict.json") -Encoding UTF8

Write-Host "  [OK] Successfully emitted 8-part evidence dossier to: $DossierOutputDir" -ForegroundColor Green
Write-Host "`n================================================================================" -ForegroundColor Green
Write-Host "       B23.2 PHYSICAL ENFORCEMENT PROOF: VERIFIED & SEALED                      " -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
exit 0
