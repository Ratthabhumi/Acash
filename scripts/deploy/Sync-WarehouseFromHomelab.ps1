# Sync the authoritative Homelab warehouse back to Windows (no market-data API calls).
#
# The Homelab is the production collector; Windows is the research/Dashboard workstation. This copies
# only the private warehouse artifacts into a staging directory, verifies every partition against the
# host manifest's SHA-256, and only then replaces the local warehouse. It never deletes data/raw, never
# sends credentials and never calls a provider.
#
#   powershell -NoProfile -File scripts/deploy/Sync-WarehouseFromHomelab.ps1
#   powershell -NoProfile -File scripts/deploy/Sync-WarehouseFromHomelab.ps1 -HostName mew@homelab -SkipResearchRebuild

param(
  [string]$HostName = "mew@homelab",
  [string]$RemoteState = "/data/acash/state/private/market_warehouse",
  [switch]$SkipResearchRebuild
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root
$local = Join-Path $root "data\private\market_warehouse"
$staging = Join-Path $root "_sync\warehouse"
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Path $staging -Force | Out-Null

Write-Host "[sync] staging from ${HostName}:${RemoteState}"
scp -q -r "${HostName}:${RemoteState}/." $staging
if (-not (Test-Path (Join-Path $staging "manifest.json"))) { throw "SYNC_MANIFEST_MISSING" }

$manifestPath = Join-Path $staging "manifest.json"
$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
$checked = 0
$failures = @()
foreach ($symbol in $manifest.partitions.PSObject.Properties.Name) {
  $entry = $manifest.partitions.$symbol
  $file = Join-Path $staging ("bars\{0}.parquet" -f $symbol)
  if (-not (Test-Path $file)) { $failures += "$symbol MISSING"; continue }
  $hash = (Get-FileHash $file -Algorithm SHA256).Hash.ToLower()
  if ($hash -ne $entry.sha256) { $failures += "$symbol HASH"; continue }
  $checked += 1
}
if ($failures.Count -gt 0) { throw "SYNC_HASH_MISMATCH: $($failures -join ', ')" }
Write-Host "[sync] $checked partitions verified against the host manifest"

# Replace only the warehouse directory, after verification. data/raw, snapshot and tax evidence stay.
New-Item -ItemType Directory -Path $local -Force | Out-Null
foreach ($name in @("bars", "fx")) {
  $source = Join-Path $staging $name
  if (Test-Path $source) {
    $target = Join-Path $local $name
    if (Test-Path $target) { Remove-Item $target -Recurse -Force }
    Copy-Item $source $target -Recurse
  }
}
foreach ($name in @("manifest.json", "session_index.json", "health.json", "job_state.json")) {
  $source = Join-Path $staging $name
  if (Test-Path $source) { Copy-Item $source (Join-Path $local $name) -Force }
}
$state = [ordered]@{
  schema = "ACASH_WAREHOUSE_SYNC_V1"
  source_host = $HostName
  synced_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  partitions_verified = $checked
  provider_calls = 0
}
$stateJson = $state | ConvertTo-Json
[System.IO.File]::WriteAllText(
  (Join-Path $local "sync_state.json"),
  $stateJson,
  (New-Object System.Text.UTF8Encoding($false))
)
Remove-Item $staging -Recurse -Force

if (-not $SkipResearchRebuild) {
  Write-Host "[sync] rebuilding the research panel from the synced warehouse (0 provider calls)"
  uv run python scripts/research_panel.py | Out-Null
}
Write-Host "[sync] done: $checked partitions, freshness in data/private/market_warehouse/health.json"
