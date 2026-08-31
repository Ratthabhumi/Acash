<#
.SYNOPSIS
    ACASH — Paper-Only Process Launcher with Secure Local Credential Injection.

.DESCRIPTION
    Retrieves Alpaca Paper credentials from the local Windows User Vault (DPAPI / SecretStore),
    validates the Paper-only security invariants, injects the credentials temporarily into the
    child execution environment, and launches the requested ACASH command.
    
    SECURITY INVARIANTS:
    - PAPER-ONLY. Live endpoint or live credentials are hard-rejected fail-closed.
    - Zero permanent environment persistence (NEVER uses setx).
    - Cleans up injected environment variables upon process completion.
    - NEVER prints secret values to console, logs, or error streams.

.PARAMETER Command
    The command and arguments to execute with Paper credentials injected.
    Example: .\scripts\run_paper.ps1 uv run pytest tests/unit/execution/test_alpaca_transport.py

.PARAMETER PreflightOnly
    Switch to run safe preflight verification and exit without executing a payload.
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory = $false)]
    [switch]$PreflightOnly,

    [Parameter(Mandatory = $false)]
    [switch]$ShowHelp,

    [Parameter(Mandatory = $false, ValueFromRemainingArguments = $true)]
    [string[]]$Command
)

$ErrorActionPreference = "Stop"

if ($ShowHelp) {
    Get-Help $MyInvocation.MyCommand.Path -Detailed
    exit 0
}

# 1. Load credentials from local Windows User Vault
$vaultFile = Join-Path -Path $env:USERPROFILE -ChildPath ".acash\paper_credentials.dpapi"

if (-not (Test-Path -Path $vaultFile)) {
    Write-Host ""
    Write-Host "[ERROR] Alpaca Paper credentials not found in local vault." -ForegroundColor Red
    Write-Host ('Vault location expected at: ' + $vaultFile) -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please run the one-time interactive setup script first:" -ForegroundColor Cyan
    Write-Host '  .\scripts\setup_paper_credentials.ps1' -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

$keyId = $null
$secret = $null

try {
    Add-Type -AssemblyName System.Security

    $encryptedBytes = [System.IO.File]::ReadAllBytes($vaultFile)
    $entropyBytes = [System.Text.Encoding]::UTF8.GetBytes("ACASH_ALPACA_PAPER_CREDENTIAL_VAULT_V1")

    $decryptedBytes = [System.Security.Cryptography.ProtectedData]::Unprotect(
        $encryptedBytes,
        $entropyBytes,
        [System.Security.Cryptography.DataProtectionScope]::CurrentUser
    )

    $jsonStr = [System.Text.Encoding]::UTF8.GetString($decryptedBytes)
    $credObj = $jsonStr | ConvertFrom-Json

    $keyId = $credObj.key_id
    $secret = $credObj.secret
    $venue = $credObj.venue

    # Clear memory references
    $jsonStr = $null
    [System.Array]::Clear($decryptedBytes, 0, $decryptedBytes.Length)

    if ($venue -ne "ALPACA_PAPER") {
        Write-Error ("[FAIL-CLOSED] Vault contains non-paper venue '" + $venue + "'. ACASH requires ALPACA_PAPER.")
        exit 1
    }

    if ([string]::IsNullOrWhiteSpace($keyId) -or [string]::IsNullOrWhiteSpace($secret)) {
        Write-Error '[FAIL-CLOSED] Retrieved credentials are empty or corrupted.'
        exit 1
    }
}
catch {
    Write-Error ('[FAIL-CLOSED] Failed to decrypt credentials from local Windows vault: ' + $_.ToString())
    exit 1
}

# 2. Inject credentials into temporary process scope and execute with cleanup
$exitCode = 0
$previousKey = $env:ACASH_ALPACA_API_KEY_ID
$previousSecret = $env:ACASH_ALPACA_API_SECRET

try {
    # Inject into process environment for child execution
    $env:ACASH_ALPACA_API_KEY_ID = $keyId
    $env:ACASH_ALPACA_API_SECRET = $secret

    # 3. Authoritative Paper-Only Guard verification via ACASH domain core
    # Resolve uv executable path across Windows environments (PS 5.1 & PS 7 compatible)
    $uvCmd = Get-Command 'uv' -ErrorAction SilentlyContinue
    $uvExe = if ($null -ne $uvCmd) { $uvCmd.Source } else { $null }
    if (-not $uvExe) {
        $candidates = @(
            (Join-Path $env:LOCALAPPDATA 'Python\pythoncore-3.14-64\Scripts\uv.exe'),
            (Join-Path $env:APPDATA 'Python\Scripts\uv.exe'),
            (Join-Path $env:USERPROFILE '.cargo\bin\uv.exe'),
            (Join-Path $PSScriptRoot '..\.venv\Scripts\uv.exe')
        )
        foreach ($c in $candidates) {
            if (Test-Path $c) {
                $uvExe = $c
                break
            }
        }
    }
    if (-not $uvExe) {
        $uvExe = 'uv'
    }

    & $uvExe run python -c "import sys; from acash.execution.alpaca.credentials import paper_credential_provider, assert_paper_venue; from acash.execution.alpaca.venue import AlpacaVenue; assert_paper_venue('ALPACA_PAPER'); p = paper_credential_provider(); assert p.venue() == 'ALPACA_PAPER', 'Venue mismatch'; assert p.load().resolved, 'Unresolved'; assert AlpacaVenue.PAPER.base_url == 'https://paper-api.alpaca.markets/v2', 'Endpoint mismatch'"
    if ($LASTEXITCODE -ne 0) {
        Write-Error '[FAIL-CLOSED] ACASH Paper-Only Guard preflight verification failed.'
        exit 1
    }

    if ($PreflightOnly) {
        Write-Host ""
        Write-Host "========================================================================" -ForegroundColor Green
        Write-Host "  [ACASH PAPER LAUNCHER] Safe Preflight Check: PASSED" -ForegroundColor Green
        Write-Host "========================================================================" -ForegroundColor Green
        Write-Host "  - Target Venue     : ALPACA_PAPER" -ForegroundColor White
        Write-Host "  - Target Endpoint  : https://paper-api.alpaca.markets/v2" -ForegroundColor White
        Write-Host "  - Credentials State: Loaded & Verified from Local Vault (DPAPI)" -ForegroundColor White
        Write-Host "  - Key ID Prefix    : $($keyId.Substring(0, [Math]::Min(4, $keyId.Length)))..." -ForegroundColor White
        Write-Host "  - Secret State     : Redacted (Protected)" -ForegroundColor White
        Write-Host "  - Live Execution   : HARD-LOCKED (OFF)" -ForegroundColor Yellow
        Write-Host "========================================================================" -ForegroundColor Green
        Write-Host ""
        exit 0
    }

    if ($null -eq $Command -or $Command.Length -eq 0) {
        Write-Host ""
        Write-Host "========================================================================" -ForegroundColor Cyan
        Write-Host "  ACASH Paper Launcher (Ready)" -ForegroundColor Cyan
        Write-Host "========================================================================" -ForegroundColor Cyan
        Write-Host 'Usage: .\scripts\run_paper.ps1 <command> [arguments...]'
        Write-Host ""
        Write-Host 'Examples:'
        Write-Host '  .\scripts\run_paper.ps1 -PreflightOnly'
        Write-Host '  .\scripts\run_paper.ps1 uv run pytest tests/unit/execution/test_alpaca_transport.py'
        Write-Host '  .\scripts\run_paper.ps1 uv run python -c "from acash.execution.alpaca.credentials import paper_credential_provider; print(paper_credential_provider().load())"'
        Write-Host ""
        exit 0
    }

    # 5. Execute user command with temporary injected credentials
    $exe = $Command[0]
    if ($exe -eq 'uv' -and $uvExe -ne 'uv') {
        $exe = $uvExe
    }
    $argsList = if ($Command.Length -gt 1) { $Command[1..($Command.Length - 1)] } else { @() }
    & $exe @argsList
    $exitCode = if ($null -ne $LASTEXITCODE) { $LASTEXITCODE } else { 0 }
}
finally {
    # 6. Strict environment cleanup: clear secrets from process scope
    if ($null -ne $previousKey) {
        $env:ACASH_ALPACA_API_KEY_ID = $previousKey
    }
    else {
        Remove-Item Env:\ACASH_ALPACA_API_KEY_ID -ErrorAction SilentlyContinue
    }

    if ($null -ne $previousSecret) {
        $env:ACASH_ALPACA_API_SECRET = $previousSecret
    }
    else {
        Remove-Item Env:\ACASH_ALPACA_API_SECRET -ErrorAction SilentlyContinue
    }

    $keyId = $null
    $secret = $null
}

exit $exitCode
