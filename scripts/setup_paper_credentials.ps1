<#
.SYNOPSIS
    ACASH — Interactive One-Time Alpaca Paper Credential Setup (Local Windows Vault).

.DESCRIPTION
    Securely stores Alpaca Paper API credentials in the current Windows User Vault
    using Windows Data Protection API (DPAPI) and/or PowerShell SecretStore.
    
    SECURITY INVARIANTS:
    - PAPER credentials only. Live credentials are strictly forbidden.
    - Secrets are encrypted with Windows DPAPI (CurrentUser scope) or SecretStore.
    - NEVER writes secrets to git, .env, source files, or plaintext logs.
    - NEVER echoes or prints secret values to console.
    - Does NOT launch ACASH or fire any orders.

.PARAMETER KeyId
    Optional Alpaca Paper API Key ID (if provided non-interactively for testing).

.PARAMETER Secret
    Optional Alpaca Paper API Secret as SecureString (if provided non-interactively for testing).
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory = $false)]
    [string]$KeyId,

    [Parameter(Mandatory = $false)]
    [System.Security.SecureString]$Secret
)

$ErrorActionPreference = 'Stop'

Write-Host '========================================================================' -ForegroundColor Cyan
Write-Host '  ACASH — Local Windows Credential Setup (Alpaca Paper Trading)' -ForegroundColor Cyan
Write-Host '========================================================================' -ForegroundColor Cyan
Write-Host ''
Write-Host 'This utility securely registers your Alpaca PAPER API credentials into'
Write-Host 'your local Windows User Vault (DPAPI / SecretStore).'
Write-Host ''
Write-Host 'SECURITY NOTICE:' -ForegroundColor Yellow
Write-Host '- PAPER credentials only. NEVER enter live trading keys.' -ForegroundColor Yellow
Write-Host '- Credentials are encrypted using your Windows user login key.' -ForegroundColor Yellow
Write-Host '- Secrets are stored completely outside the ACASH repository.' -ForegroundColor Yellow
Write-Host '- No credentials are saved in Git, .env, or plaintext files.' -ForegroundColor Yellow
Write-Host ''

# 1. Prompt for Key ID if not provided
if ([string]::IsNullOrWhiteSpace($KeyId)) {
    $KeyId = Read-Host -Prompt 'Enter Alpaca Paper API Key ID (e.g. PK...)'
}

if ([string]::IsNullOrWhiteSpace($KeyId)) {
    Write-Error '[FAIL-CLOSED] Alpaca Paper API Key ID cannot be empty.'
    exit 1
}

$KeyId = $KeyId.Trim()

# 2. Prompt for Secret Key securely if not provided
if ($null -eq $Secret) {
    $Secret = Read-Host -Prompt 'Enter Alpaca Paper Secret Key' -AsSecureString
}

if ($null -eq $Secret -or $Secret.Length -eq 0) {
    Write-Error '[FAIL-CLOSED] Alpaca Paper Secret Key cannot be empty.'
    exit 1
}

# 3. Encrypt and save to DPAPI User Vault ($env:USERPROFILE\.acash\paper_credentials.dpapi)
try {
    Add-Type -AssemblyName System.Security

    # Unsecure string safely in memory to byte array
    $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secret)
    $secretPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

    # Prepare serialized JSON payload
    $payloadObj = @{
        venue       = 'ALPACA_PAPER'
        key_id      = $KeyId
        secret      = $secretPlain
        created_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    }
    $jsonPayload = $payloadObj | ConvertTo-Json -Compress
    $payloadBytes = [System.Text.Encoding]::UTF8.GetBytes($jsonPayload)
    $entropyBytes = [System.Text.Encoding]::UTF8.GetBytes('ACASH_ALPACA_PAPER_CREDENTIAL_VAULT_V1')

    # Encrypt using Windows DPAPI CurrentUser scope
    $encryptedBytes = [System.Security.Cryptography.ProtectedData]::Protect(
        $payloadBytes,
        $entropyBytes,
        [System.Security.Cryptography.DataProtectionScope]::CurrentUser
    )

    # Clear memory references
    $secretPlain = $null
    $jsonPayload = $null
    [System.Array]::Clear($payloadBytes, 0, $payloadBytes.Length)

    # Ensure vault directory exists
    $vaultDir = Join-Path -Path $env:USERPROFILE -ChildPath '.acash'
    if (-not (Test-Path -Path $vaultDir)) {
        New-Item -Path $vaultDir -ItemType Directory -Force | Out-Null
    }

    $vaultFile = Join-Path -Path $vaultDir -ChildPath 'paper_credentials.dpapi'
    [System.IO.File]::WriteAllBytes($vaultFile, $encryptedBytes)

    # 4. Optional SecretStore integration if module is present
    if (Get-Module -ListAvailable Microsoft.PowerShell.SecretManagement) {
        try {
            Import-Module Microsoft.PowerShell.SecretManagement -ErrorAction SilentlyContinue
            Import-Module Microsoft.PowerShell.SecretStore -ErrorAction SilentlyContinue

            $vaultName = 'AcashPaperVault'
            $existingVault = Get-SecretVault -Name $vaultName -ErrorAction SilentlyContinue
            if (-not $existingVault) {
                Register-SecretVault -Name $vaultName -ModuleName Microsoft.PowerShell.SecretStore -DefaultVault:$false -ErrorAction SilentlyContinue
            }
            Set-Secret -Name 'ACASH_ALPACA_API_KEY_ID' -Secret $KeyId -Vault $vaultName -ErrorAction SilentlyContinue
            Set-Secret -Name 'ACASH_ALPACA_API_SECRET' -Secret $Secret -Vault $vaultName -ErrorAction SilentlyContinue
        } catch {
            # Non-fatal: DPAPI is the primary native vault
        }
    }

    Write-Host ''
    Write-Host '========================================================================' -ForegroundColor Green
    Write-Host '  [SUCCESS] Alpaca Paper credentials stored securely in Windows User Vault!' -ForegroundColor Green
    Write-Host '========================================================================' -ForegroundColor Green
    Write-Host ('Vault Location: ' + $vaultFile + ' (DPAPI CurrentUser Encrypted)')
    Write-Host 'Venue Scope   : ALPACA_PAPER'
    Write-Host ''
    Write-Host 'Next Step:' -ForegroundColor Cyan
    Write-Host '  Run .\scripts\run_paper.ps1 -PreflightOnly to verify your credentials.' -ForegroundColor Cyan
    Write-Host ''
} catch {
    Write-Error ('[FAIL-CLOSED] Failed to store credentials in local Windows vault: ' + $_.ToString())
    exit 1
}
