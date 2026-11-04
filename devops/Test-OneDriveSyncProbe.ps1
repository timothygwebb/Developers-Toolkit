# Test-OneDriveSyncProbe.ps1
# Answers two questions left open by Reset-OneDriveSync.ps1:
#   1) Does sync still WORK now that OneDrive.Sync.Service sits dormant?
#   2) When a real change wakes it, does it behave (~0.5%) or re-peg (~25%)?
# Drops a tiny timestamped probe file in the OneDrive root, polls up to
# 5 minutes for the sync service to wake, samples its CPU for 30s when it
# does, then deletes the probe (the delete syncs too, so it removes
# itself from the cloud as well). Deletes nothing else.
# Runtime: ~1 min if the service is already up, up to ~6 min if dormant.
# Windows PowerShell 5.1, pure ASCII.

$ErrorActionPreference = 'Continue'
$cores = (Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors
if (-not $cores -or $cores -lt 1) { $cores = 1 }

function Get-OdCpuTotal {
    $sum = (Get-Process -Name 'OneDrive.Sync.Service' -ErrorAction SilentlyContinue |
        Measure-Object -Property CPU -Sum).Sum
    if ($null -eq $sum) { return $null }
    return $sum
}

function Test-OdServiceRunning {
    return [bool](Get-Process -Name 'OneDrive.Sync.Service' -ErrorAction SilentlyContinue)
}

function Sample-OdCpu([int]$Samples) {
    # Write-Host for display; returns a single average number or $null.
    $prev = Get-OdCpuTotal
    if ($null -eq $prev) { return $null }
    $totalPct = 0.0
    for ($i = 1; $i -le $Samples; $i++) {
        Start-Sleep -Seconds 5
        $now = Get-OdCpuTotal
        if ($null -eq $now) { Write-Host '  (sync service stopped during the sample)'; return $null }
        $pct = [math]::Round((($now - $prev) / 5 / $cores) * 100, 1)
        $prev = $now
        $totalPct += $pct
        Write-Host ("  sample {0}: {1}%" -f $i, $pct)
    }
    return [math]::Round($totalPct / $Samples, 1)
}

function Get-OneDriveRoot {
    $accountsKey = 'HKCU:\Software\Microsoft\OneDrive\Accounts'
    if (Test-Path $accountsKey) {
        foreach ($acct in (Get-ChildItem $accountsKey -ErrorAction SilentlyContinue)) {
            $props = Get-ItemProperty $acct.PSPath -ErrorAction SilentlyContinue
            if ($props -and $props.UserFolder -and (Test-Path -LiteralPath $props.UserFolder)) {
                return $props.UserFolder
            }
        }
    }
    if ($env:OneDrive -and (Test-Path -LiteralPath $env:OneDrive)) { return $env:OneDrive }
    $fallback = "$env:USERPROFILE\OneDrive"
    if (Test-Path -LiteralPath $fallback) { return $fallback }
    return $null
}

Write-Output '=================================================='
Write-Output ' ONEDRIVE SYNC PROBE'
Write-Output '=================================================='
Write-Output ''

$root = Get-OneDriveRoot
if (-not $root) {
    Write-Output 'Could not find the OneDrive folder (registry, env, and default path all missed). Nothing probed.'
    return
}
Write-Output "OneDrive root: $root"
$appUp = [bool](Get-Process -Name 'OneDrive' -ErrorAction SilentlyContinue)
$svcUp = Test-OdServiceRunning
Write-Output "OneDrive app running: $appUp"
Write-Output "Sync service running at start: $svcUp"
Write-Output ''

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$probeName = "everest-sync-probe-$stamp.txt"
$probePath = Join-Path $root $probeName
"Everest sync probe. Created $stamp. Safe to delete." | Set-Content -LiteralPath $probePath -Encoding ASCII
Write-Output "Probe file dropped: $probePath"
$item = Get-Item -LiteralPath $probePath -Force -ErrorAction SilentlyContinue
if ($item) { Write-Output ("  attributes at drop: {0}" -f $item.Attributes) }
Write-Output ''

$avg = $null
$woke = $svcUp
if (-not $svcUp) {
    Write-Output '--- Watching for the sync service to wake (up to 300s) ---'
    $waited = 0
    while ($waited -lt 300 -and -not $woke) {
        Start-Sleep -Seconds 10
        $waited += 10
        if (Test-OdServiceRunning) {
            $woke = $true
            Write-Output "  sync service woke after ~$waited s"
        } elseif ($waited % 30 -eq 0) {
            Write-Output "  still dormant... $waited s"
        }
    }
}

$verdict = ''
if ($woke) {
    Write-Output '--- Sampling the awake service (30s) ---'
    Start-Sleep -Seconds 5
    $avg = Sample-OdCpu 6
    $item2 = Get-Item -LiteralPath $probePath -Force -ErrorAction SilentlyContinue
    if ($item2) { Write-Output ("Probe attributes now: {0}" -f $item2.Attributes) }
    Write-Output ''
    if ($null -eq $avg) {
        $verdict = 'INCONCLUSIVE - the service woke, then stopped during sampling. Start/stop cycling is itself a symptom worth noting; re-run Check-OneDriveAndRam.ps1 in a few minutes.'
    } elseif ($avg -ge 15) {
        $verdict = "RE-PEGGED ON WAKE - average $avg%. Waking the service brings the burn back, so the restart cure did not hold. Durable fix: selective sync (OneDrive Settings > Account > Choose folders) - untick Webb Hosting Services Backups (144 GB), Apps (118 GB), Imports (45 GB) on this machine - then re-run this probe."
    } elseif ($avg -lt 5) {
        $verdict = "SYNC PATH ALIVE, SERVICE BEHAVES - average $avg% with a fresh change to process. The dormant service was simply demand-started and idle-healthy, exactly what we want. OneDrive is fixed; nothing further to do unless it re-pegs days from now."
    } else {
        $verdict = "ALIVE BUT WARM - average $avg%. It woke and worked without pegging; possibly still verifying after the probe. Acceptable; re-check with Check-OneDriveAndRam.ps1 tomorrow - settled under 5% is the healthy steady state."
    }
} else {
    $verdict = 'SERVICE SLEPT THROUGH A PENDING CHANGE - 5 minutes with a new file in the root and the sync service never started, so right now new files are NOT actively syncing. The CPU burn stays zero, but sync is stalled until something wakes the service: click the OneDrive tray icon and open the app window, confirm it does not show an error, then re-run this probe. If it still sleeps, sign out of OneDrive and back in (Settings > Account) - that re-registers the service.'
}
Write-Output "VERDICT: $verdict"
Write-Output ''

Write-Output '--- Cleanup ---'
Remove-Item -LiteralPath $probePath -Force -ErrorAction SilentlyContinue
if (Test-Path -LiteralPath $probePath) {
    Write-Output "  probe file still present (locked?) - delete it manually: $probePath"
} else {
    Write-Output '  probe file deleted locally; the delete syncs, removing the cloud copy too.'
}
Write-Output ''
try {
    $h = Invoke-RestMethod -Uri 'http://127.0.0.1:8002/api/speedup/health' -TimeoutSec 5
    Write-Output ("SpeedUp now: cpu={0} ram={1} disk={2} score={3}" -f $h.cpu, $h.ram, $h.disk, $h.score)
} catch {
    Write-Output 'SpeedUp: still not answering on :8002 (stack/backend down - separate thread).'
}
Write-Output ''
Write-Output 'Done. Paste this whole output back to Everest.'
