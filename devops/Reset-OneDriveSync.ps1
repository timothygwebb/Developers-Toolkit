# Reset-OneDriveSync.ps1  (v2)
# v2 fixes v1: (a) the sampler printed with Write-Output while also
# returning the average, so the result arrived as a text+number array and
# Classify crashed on it - sample lines now use Write-Host; (b) v1 only
# waited 30s for the sync service to return after restart and called it
# inconclusive - v2 waits up to 3 minutes and handles the service being
# already down (which is the state v1 left the machine in, burner dead).
#
# Flow: baseline 15s (if running) -> clean restart -> wait for the sync
# service to return (up to 180s) -> settle 20s -> verdict sample 30s ->
# escalate to OneDrive.exe /reset ONLY if pegged again (>=15%), settle
# 60s, final sample 30s. Local files are never deleted by any of this.
# Worst case runtime ~6 minutes. Windows PowerShell 5.1, pure ASCII.

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
    # Display goes to Write-Host ONLY; the return value is a single number
    # (average % of total machine CPU) or $null if the service vanishes.
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

function Classify([double]$Avg) {
    if ($Avg -lt 5)  { return 'CURED / quiet (under 5%)' }
    if ($Avg -lt 15) { return 'ELEVATED (5-15%) - working, watch it' }
    return 'PEGGED (over 15%) - still stuck'
}

function Find-OneDriveExe {
    foreach ($p in @("$env:LOCALAPPDATA\Microsoft\OneDrive\OneDrive.exe",
                     'C:\Program Files\Microsoft OneDrive\OneDrive.exe',
                     'C:\Program Files (x86)\Microsoft OneDrive\OneDrive.exe')) {
        if (Test-Path -LiteralPath $p) { return $p }
    }
    return $null
}

function Wait-ForSyncService([int]$TimeoutSec) {
    $waited = 0
    while ($waited -lt $TimeoutSec) {
        if (Test-OdServiceRunning) {
            Write-Host "  sync service is back (after ~$waited s)"
            return $true
        }
        Start-Sleep -Seconds 10
        $waited += 10
        Write-Host "  waiting for sync service... $waited s"
    }
    return $false
}

function Restart-OneDrive {
    foreach ($n in @('OneDrive.Sync.Service', 'OneDrive')) {
        Get-Process -Name $n -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Output ("  stopping process {0} (PID {1})" -f $_.ProcessName, $_.Id)
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 3
    $exe = Find-OneDriveExe
    if ($exe) {
        Write-Output "  relaunching: $exe"
        Start-Process -FilePath $exe -ErrorAction SilentlyContinue
    } else {
        Write-Output '  WARNING: OneDrive.exe not found in the usual paths - relaunch it manually from the Start menu.'
    }
}

Write-Output '=================================================='
Write-Output ' ONEDRIVE RESTART + VERDICT (v2)'
Write-Output '=================================================='
Write-Output ''

$base = $null
if (Test-OdServiceRunning) {
    Write-Output '--- Baseline (15s) ---'
    $base = Sample-OdCpu 3
    if ($null -ne $base) { Write-Output ("Baseline average: {0}%  -> {1}" -f $base, (Classify $base)) }
    Write-Output ''
    Write-Output '--- Restarting OneDrive ---'
    Restart-OneDrive
    Write-Output ''
} else {
    Write-Output 'Sync service is not running right now (this is the state the v1'
    Write-Output 'run left behind: the pegged process was killed and never came'
    Write-Output 'back). Making sure the OneDrive app is up so the service can'
    Write-Output 'return, then watching for it.'
    if (-not (Get-Process -Name 'OneDrive' -ErrorAction SilentlyContinue)) {
        $exe = Find-OneDriveExe
        if ($exe) { Start-Process -FilePath $exe -ErrorAction SilentlyContinue; Write-Output "  started: $exe" }
    } else {
        Write-Output '  OneDrive app process is running.'
    }
    Write-Output ''
}

Write-Output '--- Waiting for the sync service (up to 180s) ---'
$back = Wait-ForSyncService 180
$finalVerdict = ''
if (-not $back) {
    $appState = 'not running'
    if (Get-Process -Name 'OneDrive' -ErrorAction SilentlyContinue) { $appState = 'running' }
    $finalVerdict = "VERDICT: SERVICE STAYED DOWN. OneDrive app is $appState, but the sync service never started in 3 minutes. The CPU burn is gone because the burner is not running; sync itself is paused until the service next starts (sign-in, app activity). Click the OneDrive tray icon / open the app, give it a minute, then re-run this script - if the service returns pegged, it will escalate to /reset."
    Write-Output $finalVerdict
} else {
    Write-Output '--- Settling 20s, then verdict sample (30s) ---'
    Start-Sleep -Seconds 20
    $after = Sample-OdCpu 6
    if ($null -eq $after) {
        $finalVerdict = 'INCONCLUSIVE - the service started, then stopped again during sampling. That start/stop cycling is itself a symptom; note it and re-run Check-OneDriveAndRam.ps1 in a few minutes.'
        Write-Output $finalVerdict
    } else {
        Write-Output ("Post-restart average: {0}%  -> {1}" -f $after, (Classify $after))
        if ($after -ge 15) {
            Write-Output ''
            Write-Output '--- Re-pegged after restart. Escalating: OneDrive /reset ---'
            Write-Output '    (/reset forces a clean re-index. Local files are NOT deleted.)'
            $exe = Find-OneDriveExe
            if ($exe) {
                Start-Process -FilePath $exe -ArgumentList '/reset' -ErrorAction SilentlyContinue
                Write-Output '    reset issued; it restarts OneDrive itself. Waiting for the service, then settling...'
                $back2 = Wait-ForSyncService 180
                if ($back2) {
                    Start-Sleep -Seconds 30
                    Write-Output '--- Post-reset sample (30s) ---'
                    $postReset = Sample-OdCpu 6
                    if ($null -eq $postReset) {
                        $finalVerdict = 'INCONCLUSIVE - service vanished during the post-reset sample. Re-run Check-OneDriveAndRam.ps1 in a few minutes.'
                    } elseif ($postReset -lt 15) {
                        $finalVerdict = "RESET WORKED - post-reset average $postReset%. A fresh re-index of a ~584 GB namespace can run warm for a while; re-run Check-OneDriveAndRam.ps1 later today - settled under 5% means done."
                    } else {
                        $finalVerdict = "STILL PEGGED after /reset (average $postReset%). The service is stuck on the namespace itself. Durable fix: selective sync - OneDrive Settings > Account > Choose folders, and untick the big ones this machine does not need locally (your largest folders - example: Backups, Apps, Imports) - then re-sample."
                    }
                } else {
                    $finalVerdict = 'INCONCLUSIVE - after /reset the sync service did not return within 3 minutes. Open the OneDrive app, confirm it says it is starting/syncing, then re-run Check-OneDriveAndRam.ps1.'
                }
            } else {
                $finalVerdict = 'Could not run /reset - OneDrive.exe not found in the usual paths.'
            }
            Write-Output $finalVerdict
        } elseif ($after -lt 5) {
            $finalVerdict = "CURED - post-restart average $after%. The service had wedged and a clean restart cleared it; no /reset needed. If it re-pegs over the coming days, that pattern points at the oversized namespace - selective sync is the durable fix."
            Write-Output $finalVerdict
        } else {
            $finalVerdict = "IMPROVED but warm - post-restart average $after%. Likely verification work after the restart. Give it 15 minutes, re-run Check-OneDriveAndRam.ps1; flat above 15% again means run this script once more and it will escalate to /reset."
            Write-Output $finalVerdict
        }
    }
}
Write-Output ''
try {
    $h = Invoke-RestMethod -Uri 'http://127.0.0.1:8002/api/health' -TimeoutSec 5
    Write-Output ("LocalHealth now: cpu={0} ram={1} disk={2} score={3}" -f $h.cpu, $h.ram, $h.disk, $h.score)
} catch {
    Write-Output 'LocalHealth: still not answering on :8002 (stack/backend down - separate thread).'
}
Write-Output ''
Write-Output 'Done. Done.'
