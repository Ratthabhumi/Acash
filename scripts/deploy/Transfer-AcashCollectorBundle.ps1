# Transfer the ACASH collector bundle to the Homelab over the authenticated SSH route.
#
# Builds one tar archive containing only what the collector needs (no secrets, no Git history, no
# full data/raw), copies it with scp, and prints the SHA-256 so the host can verify the transfer.
#
#   powershell -NoProfile -File scripts/deploy/Transfer-AcashCollectorBundle.ps1
#   powershell -NoProfile -File scripts/deploy/Transfer-AcashCollectorBundle.ps1 -HostName mew@homelab
#
# The Owner still has to create /etc/acash/market-data.env and run the installer with sudo; this script
# never reads or sends a credential.

param(
  [string]$HostName = "mew@homelab",
  [string]$RemotePath = "~/acash-bundle",
  [string]$BundleRoot = "_bundle"
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

$bundle = Join-Path $root $BundleRoot
if (Test-Path $bundle) { Remove-Item $bundle -Recurse -Force }
New-Item -ItemType Directory -Path (Join-Path $bundle "app") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $bundle "deploy") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $bundle "warehouse") -Force | Out-Null

Write-Host "[transfer] staging code subset (src + scripts + docs template)"
Copy-Item -Recurse src (Join-Path $bundle "app\src")
Copy-Item -Recurse scripts (Join-Path $bundle "app\scripts")
New-Item -ItemType Directory -Path (Join-Path $bundle "app\docs\operations") -Force | Out-Null
Copy-Item docs\operations\market-data-collector-homelab.md (Join-Path $bundle "app\docs\operations")
# Public, non-secret artifacts the runtime needs on the host: the retention gate reads the ratified
# ODR record, and the session calendar reads the venue fixture.
New-Item -ItemType Directory -Path (Join-Path $bundle "app\docs\governance") -Force | Out-Null
Copy-Item docs\governance\*.json (Join-Path $bundle "app\docs\governance")
Copy-Item docs\governance\*.md (Join-Path $bundle "app\docs\governance") -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path (Join-Path $bundle "app\docs\research\evidence") -Force | Out-Null
Copy-Item docs\research\evidence\nyse_xnys_calendar_2026_2028.json (Join-Path $bundle "app\docs\research\evidence")
Copy-Item docs\operations\homelab-collector-deployment-20261105.md (Join-Path $bundle "app\docs\operations") -ErrorAction SilentlyContinue

Write-Host "[transfer] staging unit templates and installer"
Copy-Item docs\operations\acash-market-collector.service (Join-Path $bundle "deploy")
Copy-Item docs\operations\acash-market-collector.timer (Join-Path $bundle "deploy")
Copy-Item scripts\deploy\deploy_acash_collector.sh (Join-Path $bundle "deploy")

Write-Host "[transfer] staging private warehouse (partitions + manifest + FX artifacts, no secrets)"
$warehouse = Join-Path $root "data\private\market_warehouse"
if (Test-Path $warehouse) {
  Copy-Item -Recurse (Join-Path $warehouse "bars") (Join-Path $bundle "warehouse\bars") -ErrorAction SilentlyContinue
  foreach ($name in @("manifest.json", "session_index.json", "health.json", "job_state.json")) {
    $source = Join-Path $warehouse $name
    if (Test-Path $source) { Copy-Item $source (Join-Path $bundle "warehouse") }
  }
  $fx = Join-Path $warehouse "fx"
  if (Test-Path $fx) { Copy-Item -Recurse $fx (Join-Path $bundle "warehouse\fx") }
}
$snapshot = Join-Path $root "data\private\snapshot.json"
if (Test-Path $snapshot) { Copy-Item $snapshot (Join-Path $bundle "snapshot.json") }

$archive = Join-Path $root "acash-collector-bundle.tar.gz"
if (Test-Path $archive) { Remove-Item $archive -Force }
Write-Host "[transfer] creating archive"
tar -czf $archive -C $bundle .

$hash = (Get-FileHash $archive -Algorithm SHA256).Hash.ToLower()
Write-Host "[transfer] bundle SHA-256: $hash"

Write-Host "[transfer] copying to ${HostName}:${RemotePath}"
ssh $HostName "mkdir -p $RemotePath"
scp $archive "${HostName}:${RemotePath}/"

Write-Host "[transfer] verifying the archive hash on the host"
$remoteHash = (ssh $HostName "sha256sum $RemotePath/acash-collector-bundle.tar.gz | cut -d' ' -f1").Trim()
if ($remoteHash -ne $hash) { throw "TRANSFER_HASH_MISMATCH: local $hash remote $remoteHash" }
ssh $HostName "cd $RemotePath && tar -xzf acash-collector-bundle.tar.gz && echo extracted"
Write-Host "[transfer] done. Next (Owner, on the host):"
Write-Host "  1) sudo install -d -m 0700 /etc/acash && sudo install -m 0600 /dev/null /etc/acash/market-data.env && sudoedit /etc/acash/market-data.env"
Write-Host "  2) sudo $RemotePath/deploy/deploy_acash_collector.sh            # installs + acceptance pass"
Write-Host "  3) sudo $RemotePath/deploy/deploy_acash_collector.sh --enable   # only after reviewing health"
