# Check-OneDriveAndRam.ps1
# Follow-up to Diagnose-And-Clean-Machine.ps1:
#  1) OneDrive.Sync.Service: samples CPU for 60 seconds (sustained burn =
#     sync loop; a spike that dies off = just catching up), lists the sync
#     roots from the registry, sizes their top folders, counts files changed
#     in the last hour (churn), and checks whether source / Downloads /
#     Documents live INSIDE a OneDrive root.
#  2) RAM by APP (all PIDs summed per app, not per process).
#  3) SpeedUp health at the start and end of the sample window.
# Report-only: deletes nothing, changes nothing.
# Windows PowerShell 5.1, pure ASCII.

$ErrorActionPreference = 'Continue'

function Show-SpeedUpHealth([string]$Label) {
    try {
        $h = Invoke-RestMethod -Uri 'http://127.0.0.1:8002/api/speedup/health' -TimeoutSec 5
        Write-Output ("SpeedUp ($Label): cpu={0} ram={1} disk={2} score={3}" -f $h.cpu, $h.ram, $h.disk, $h.score)
    } catch {
        Write-Output "SpeedUp ($Label): not answering on :8002"
    }
}

Write-Output '=================================================='
Write-Output ' ONEDRIVE + RAM FOLLOW-UP'
Write-Output '=================================================='
Write-Output ''
Show-SpeedUpHealth 'window start'
Write-Output ''

# ---------------- OneDrive sync roots ----------------
Write-Output '--- OneDrive sync roots (from registry + env) ---'
$roots = @()
$accountsKey = 'HKCU:\Software\Microsoft\OneDrive\Accounts'
if (Test-Path $accountsKey) {
    Get-ChildItem $accountsKey -ErrorAction SilentlyContinue | ForEach-Object {
        $props = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
        if ($props -and $props.UserFolder) {
            $roots += [pscustomobject]@{ Account = $_.PSChildName; Root = $props.UserFolder; DisplayName = $props.DisplayName }
        }
    }
}
foreach ($envName in @('OneDrive', 'OneDriveConsumer', 'OneDriveCommercial')) {
    $v = [Environment]::GetEnvironmentVariable($envName)
    if ($v -and ($roots.Root -notcontains $v)) {
        $roots += [pscustomobject]@{ Account = "env:$envName"; Root = $v; DisplayName = '' }
    }
}
if ($roots.Count -eq 0) { Write-Output '  (no OneDrive sync roots found)' }
foreach ($r in $roots) { Write-Output ("  [{0}] {1}" -f $r.Account, $r.Root) }
Write-Output ''

# Are the churn-heavy folders inside a sync root?
Write-Output '--- Are your busy folders inside a OneDrive root? ---'
$busy = @("$env:USERPROFILE\source", "$env:USERPROFILE\Downloads", "$env:USERPROFILE\Documents", "$env:USERPROFILE\Desktop")
foreach ($b in $busy) {
    $inside = $false
    foreach ($r in $roots) {
        if ($b.StartsWith($r.Root, [System.StringComparison]::OrdinalIgnoreCase)) { $inside = $true }
    }
    Write-Output ("  {0,-45} inside OneDrive: {1}" -f $b, $inside)
}
Write-Output ''

# Top folders inside each root + recent churn
foreach ($r in $roots) {
    Write-Output ("--- Inside {0} ---" -f $r.Root)
    if (Test-Path -LiteralPath $r.Root) {
        Get-ChildItem -LiteralPath $r.Root -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
            $sum = (Get-ChildItem -LiteralPath $_.FullName -Recurse -Force -File -ErrorAction SilentlyContinue |
                Measure-Object -Property Length -Sum).Sum
            if ($null -eq $sum) { $sum = 0 }
            [pscustomobject]@{ GB = [math]::Round($sum / 1GB, 2); Folder = $_.FullName }
        } | Sort-Object GB -Descending | Select-Object -First 10 | ForEach-Object {
            Write-Output ("  {0,8} GB  {1}" -f $_.GB, $_.Folder)
        }
        $hourAgo = (Get-Date).AddHours(-1)
        $churn = @(Get-ChildItem -LiteralPath $r.Root -Recurse -Force -File -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -gt $hourAgo }).Count
        Write-Output "  Files modified in the last hour under this root: $churn"
    } else {
        Write-Output '  (root folder not found on disk)'
    }
    Write-Output ''
}

# ---------------- OneDrive CPU sample ----------------
Write-Output '--- OneDrive CPU sample: 60 seconds, one reading every 5s ---'
$cores = (Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors
if (-not $cores -or $cores -lt 1) { $cores = 1 }
$odNames = @('OneDrive.Sync.Service', 'OneDrive')
$tracked = @{}
foreach ($n in $odNames) {
    Get-Process -Name $n -ErrorAction SilentlyContinue | ForEach-Object {
        $tracked[$_.Id] = @{ Name = $_.ProcessName; FirstCPU = $_.CPU; LastCPU = $_.CPU; RAM = 0 }
    }
}
if ($tracked.Count -eq 0) {
    Write-Output '  (no OneDrive processes running)'
} else {
    foreach ($k in $tracked.Keys) { Write-Output ("  tracking PID {0} ({1})" -f $k, $tracked[$k].Name) }
    for ($i = 1; $i -le 12; $i++) {
        Start-Sleep -Seconds 5
        $line = "  t={0,2}s" -f ($i * 5)
        foreach ($k in @($tracked.Keys)) {
            $p = Get-Process -Id $k -ErrorAction SilentlyContinue
            if ($p) {
                $delta = $p.CPU - $tracked[$k].LastCPU
                $tracked[$k].LastCPU = $p.CPU
                $tracked[$k].RAM = [math]::Round($p.WorkingSet64 / 1MB, 0)
                $pct = [math]::Round(($delta / 5 / $cores) * 100, 1)
                $line += "  PID $k cpu-last-5s: $pct%"
            } else {
                $line += "  PID $k exited"
                $tracked.Remove($k)
            }
        }
        Write-Output $line
    }
    Write-Output '  --- totals over the 60s window ---'
    foreach ($k in $tracked.Keys) {
        $totalDelta = $tracked[$k].LastCPU - $tracked[$k].FirstCPU
        $avg = [math]::Round(($totalDelta / 60 / $cores) * 100, 1)
        Write-Output ("  PID {0} ({1}): {2} sec CPU in 60s = avg {3}% of machine, RAM {4} MB" -f $k, $tracked[$k].Name, [math]::Round($totalDelta, 1), $avg, $tracked[$k].RAM)
    }
    Write-Output '  Reading it: sustained double digits = sync loop. Near zero after'
    Write-Output '  the first sample or two = it was just finishing a batch.'
}
Write-Output ''

# ---------------- RAM by app ----------------
Write-Output '--- RAM by app (all PIDs summed) ---'
$os = Get-CimInstance Win32_OperatingSystem
$totalGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
$freeGB = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
Write-Output "  Machine: $totalGB GB total, $freeGB GB free"
Get-Process -ErrorAction SilentlyContinue |
    Group-Object ProcessName |
    ForEach-Object {
        $ws = ($_.Group | Measure-Object -Property WorkingSet64 -Sum).Sum
        [pscustomobject]@{ MB = [math]::Round($ws / 1MB, 0); PIDs = $_.Count; App = $_.Name }
    } |
    Sort-Object MB -Descending |
    Select-Object -First 15 |
    ForEach-Object { Write-Output ("  {0,-28} {1,6} PIDs  {2,8} MB" -f $_.App, $_.PIDs, $_.MB) }
Write-Output ''
Show-SpeedUpHealth 'window end'
Write-Output ''
Write-Output 'Done. Paste this whole output back to Everest.'
