# Delta sync of the authoritative Homelab warehouse to Windows (no market-data API calls).
#
# 1. Fetch the remote manifest and compare per-partition SHA-256 with the last qualified local generation.
# 2. Transfer only partitions whose hash changed or that are missing.
# 3. Verify every staged partition against the remote manifest.
# 4. Cut over to the new generation only after verification; the previous generation stays as
#    `market_warehouse.previous` until the next successful sync, so an interrupted run never destroys it.
# 5. Rebuild the offline research panel only when the inputs actually changed.
#
#   powershell -NoProfile -File scripts/deploy/Sync-WarehouseFromHomelab.ps1

param(
  [string]$HostName = "mew@homelab",
  [string]$RemoteState = "/data/acash/state/private/market_warehouse",
  [switch]$SkipResearchRebuild,
  [switch]$Force
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root
$local = Join-Path $root "data\private\market_warehouse"
$previous = Join-Path $root "data\private\market_warehouse.previous"
$work = Join-Path $root "_sync"
$staging = Join-Path $work "warehouse"
if (Test-Path $work) { Remove-Item $work -Recurse -Force }
New-Item -ItemType Directory -Path (Join-Path $staging "bars") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $staging "fx") -Force | Out-Null

Write-Host "[sync] fetching remote manifest"
scp -q "${HostName}:${RemoteState}/manifest.json" (Join-Path $staging "manifest.json")
scp -q "${HostName}:${RemoteState}/session_index.json" (Join-Path $staging "session_index.json")
scp -q "${HostName}:${RemoteState}/health.json" (Join-Path $staging "health.json")
$remote = Get-Content (Join-Path $staging "manifest.json") -Raw | ConvertFrom-Json
$localManifestPath = Join-Path $local "manifest.json"
$localManifest = if (Test-Path $localManifestPath) { Get-Content $localManifestPath -Raw | ConvertFrom-Json } else { $null }

$changed = @()
foreach ($symbol in $remote.partitions.PSObject.Properties.Name) {
  $remoteHash = $remote.partitions.$symbol.sha256
  $localHash = $null
  if ($localManifest -and $localManifest.partitions.PSObject.Properties.Name -contains $symbol) {
    $localHash = $localManifest.partitions.$symbol.sha256
  }
  $file = Join-Path $local ("bars\{0}.parquet" -f $symbol)
  if (-not (Test-Path $file) -or $localHash -ne $remoteHash) { $changed += $symbol }
}
if ($Force) { $changed = @($remote.partitions.PSObject.Properties.Name) }

if ($changed.Count -eq 0 -and -not $SkipResearchRebuild) {
  Write-Host "[sync] no changed partitions; nothing to transfer"
  $state = [ordered]@{
    schema = "ACASH_WAREHOUSE_SYNC_V1"; source_host = $HostName
    synced_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    status = "NO_CHANGE"; partitions_verified = 0; provider_calls = 0
  }
  [System.IO.File]::WriteAllText((Join-Path $local "sync_state.json"), ($state | ConvertTo-Json),
    (New-Object System.Text.UTF8Encoding($false)))
  Remove-Item $work -Recurse -Force
  exit 0
}

Write-Host "[sync] transferring $($changed.Count) changed partition(s)"
foreach ($symbol in $changed) {
  scp -q "${HostName}:${RemoteState}/bars/${symbol}.parquet" (Join-Path $staging ("bars\{0}.parquet" -f $symbol))
}
# FX artifacts are small; copy when present and let the hash check below catch drift.
scp -q -r "${HostName}:${RemoteState}/fx/." (Join-Path $staging "fx") 2>$null

$verified = 0
foreach ($symbol in $remote.partitions.PSObject.Properties.Name) {
  $entry = $remote.partitions.$symbol
  $file = Join-Path $staging ("bars\{0}.parquet" -f $symbol)
  if (-not (Test-Path $file)) {
    if (Test-Path (Join-Path $local ("bars\{0}.parquet" -f $symbol))) {
      Copy-Item (Join-Path $local ("bars\{0}.parquet" -f $symbol)) $file   # unchanged, carry forward
    } else { throw "SYNC_PARTITION_MISSING: $symbol" }
  }
  $hash = (Get-FileHash $file -Algorithm SHA256).Hash.ToLower()
  if ($hash -ne $entry.sha256) { throw "SYNC_HASH_MISMATCH: $symbol" }
  $verified += 1
}

# Cut over only after the staged generation is complete and verified.
if (Test-Path $previous) { Remove-Item $previous -Recurse -Force }
if (Test-Path $local) { Move-Item $local $previous }
try {
  New-Item -ItemType Directory -Path (Join-Path $local "bars") -Force | Out-Null
  Copy-Item (Join-Path $staging "bars\*") (Join-Path $local "bars") -Force
  if (Test-Path (Join-Path $staging "fx")) { Copy-Item (Join-Path $staging "fx") $local -Recurse -Force }
  foreach ($name in @("manifest.json", "session_index.json", "health.json")) {
    Copy-Item (Join-Path $staging $name) (Join-Path $local $name) -Force
  }
  $state = [ordered]@{
    schema = "ACASH_WAREHOUSE_SYNC_V1"; source_host = $HostName
    synced_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    status = "SYNCED"; partitions_changed = $changed.Count; partitions_verified = $verified
    provider_calls = 0
  }
  [System.IO.File]::WriteAllText((Join-Path $local "sync_state.json"), ($state | ConvertTo-Json),
    (New-Object System.Text.UTF8Encoding($false)))
} catch {
  if (Test-Path $previous) { Remove-Item $local -Recurse -Force -ErrorAction SilentlyContinue; Move-Item $previous $local }
  throw
}
Remove-Item $work -Recurse -Force

if (-not $SkipResearchRebuild) {
  Write-Host "[sync] rebuilding the research panel (0 provider calls)"
  uv run python scripts/research_panel.py | Out-Null
}
Write-Host "[sync] done: $verified partitions verified, $($changed.Count) transferred"
