# Register or update the Windows-side warehouse sync (after the 01:00 ET Homelab collection window).
#
# 13:30 ICT Tuesday-Saturday covers the 01:00 ET Tue-Sat collector run including US DST, and
# -StartWhenAvailable recovers a missed run after the workstation was asleep or offline.
# The task runs as the current user, never stores credentials, and only invokes the sync script.
# Re-running is idempotent: an existing task keeps its trigger, settings and principal and only its
# action is updated to the current `-Scheduled` contract.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/deploy/Register-AcashSyncTask.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/deploy/Register-AcashSyncTask.ps1 -Unregister

param([switch]$Unregister)

$ErrorActionPreference = "Stop"
$taskName = "ACASH Warehouse Sync"
if ($Unregister) {
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Host "[task] removed (if it existed)"
  exit 0
}

$script = Join-Path $PSScriptRoot "Sync-WarehouseFromHomelab.ps1"
if (-not (Test-Path $script)) { throw "SYNC_SCRIPT_MISSING" }

$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$script`" -Scheduled"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existing) {
  $current = ($existing.Actions | Select-Object -First 1).Arguments
  if ($current -ne $arguments) {
    Set-ScheduledTask -TaskName $taskName -Action $action | Out-Null
    Write-Host "[task] action updated (schedule/principal preserved)"
  } else {
    Write-Host "[task] action already current"
  }
} else {
  $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday, Wednesday, Thursday, Friday, Saturday -At "13:30"
  $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
  $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
  Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings `
    -Principal $principal -Description "ACASH: delta sync of the Homelab market-data warehouse (no provider calls)" -Force | Out-Null
  Write-Host "[task] registered"
}

$info = Get-ScheduledTask -TaskName $taskName
$next = (Get-ScheduledTaskInfo -TaskName $taskName).NextRunTime
Write-Host "[task] state=$($info.State) next=$next action=$arguments"
