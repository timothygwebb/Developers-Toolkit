# Diagnose-And-Clean-Machine.ps1
# 1) Shows what LocalHealth sees (cpu / ram / disk / score) before cleanup
# 2) Reports the biggest disk consumers and the top CPU / RAM processes
# 3) Frees SAFE junk only: temp files older than 24h, the Recycle Bin,
#    and the Windows Update download cache
# 4) Re-reads free space + LocalHealth score so the gain is visible
# Nothing outside those junk paths is deleted. No admin required;
# admin-only items are attempted and reported if they could not clear.
# Windows PowerShell 5.1, pure ASCII.

$ErrorActionPreference = 'Continue'

function Get-FreeGB([string]$Letter) {
    $d = Get-PSDrive -Name $Letter -ErrorAction SilentlyContinue
    if ($d) { return [math]::Round($d.Free / 1GB, 2) }
    return -1
}

function Get-DirGB([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    $sum = (Get-ChildItem -LiteralPath $Path -Recurse -Force -File -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum
    if ($null -eq $sum) { $sum = 0 }
    return [math]::Round($sum / 1GB, 2)
}

function Show-LocalHealth([string]$Label) {
    Write-Output "--- Local health ($Label) ---"
    try {
        $h = Invoke-RestMethod -Uri 'http://127.0.0.1:8002/api/health' -TimeoutSec 5
        $h | ConvertTo-Json -Depth 4
    } catch {
        Write-Output "  (LocalHealth backend not answering on :8002 - start the stack to see the score)"
    }
    Write-Output ''
}

Write-Output '=================================================='
Write-Output ' MACHINE LOAD DIAGNOSIS + SAFE CLEANUP'
Write-Output '=================================================='
Write-Output ''

Show-LocalHealth 'BEFORE'

$freeBefore = Get-FreeGB 'C'
Write-Output "C: free space BEFORE: $freeBefore GB"
Write-Output ''
Write-Output '--- Drives ---'
Get-PSDrive -PSProvider FileSystem | ForEach-Object {
    $used = [math]::Round($_.Used / 1GB, 1)
    $free = [math]::Round($_.Free / 1GB, 1)
    $total = $used + $free
    $pct = 0
    if ($total -gt 0) { $pct = [math]::Round(($used / $total) * 100, 1) }
    Write-Output ("  {0}: {1} GB used / {2} GB total ({3}% full), {4} GB free" -f $_.Name, $used, $total, $pct, $free)
}
Write-Output ''

Write-Output '--- Biggest folders (GB) ---'
$candidates = @(
    "$env:USERPROFILE\Downloads",
    "$env:USERPROFILE\Documents",
    "$env:USERPROFILE\source",
    "$env:USERPROFILE\.nuget\packages",
    "$env:USERPROFILE\.cache",
    "$env:LOCALAPPDATA\Temp",
    "$env:LOCALAPPDATA\npm-cache",
    "$env:LOCALAPPDATA\pip\Cache",
    "$env:LOCALAPPDATA\Docker",
    'C:\Windows\Temp',
    'C:\Windows\SoftwareDistribution\Download'
)
foreach ($c in $candidates) {
    $gb = Get-DirGB $c
    if ($null -ne $gb) { Write-Output ("  {0,8} GB  {1}" -f $gb, $c) }
}
$rbBytes = 0
Get-ChildItem 'C:\$Recycle.Bin' -Recurse -Force -File -ErrorAction SilentlyContinue | ForEach-Object { $rbBytes += $_.Length }
Write-Output ("  {0,8} GB  C:\`$Recycle.Bin" -f [math]::Round($rbBytes / 1GB, 2))
foreach ($sysFile in @('C:\hiberfil.sys', 'C:\pagefile.sys', 'C:\swapfile.sys')) {
    $f = Get-Item -LiteralPath $sysFile -Force -ErrorAction SilentlyContinue
    if ($f) { Write-Output ("  {0,8} GB  {1} (system file, report only)" -f [math]::Round($f.Length / 1GB, 2), $sysFile) }
}
Write-Output ''

Write-Output '--- node_modules under source\repos (GB each) ---'
$reposRoot = "$env:USERPROFILE\source\repos"
if (Test-Path -LiteralPath $reposRoot) {
    Get-ChildItem -LiteralPath $reposRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        foreach ($sub in @('node_modules', 'frontend\node_modules', 'backend\node_modules')) {
            $p = Join-Path $_.FullName $sub
            $gb = Get-DirGB $p
            if ($null -ne $gb -and $gb -gt 0) { Write-Output ("  {0,8} GB  {1}" -f $gb, $p) }
        }
    }
}
Write-Output ''

Write-Output '--- Memory ---'
$os = Get-CimInstance Win32_OperatingSystem
$totalGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
$freeGB = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
$usedGB = [math]::Round($totalGB - $freeGB, 1)
$ramPct = 0
if ($totalGB -gt 0) { $ramPct = [math]::Round(($usedGB / $totalGB) * 100, 1) }
Write-Output "  RAM: $usedGB GB used / $totalGB GB total ($ramPct%), $freeGB GB free"
Write-Output ''
Write-Output '--- Top 12 processes by RAM (working set) ---'
Get-Process -ErrorAction SilentlyContinue |
    Sort-Object WorkingSet64 -Descending |
    Select-Object -First 12 |
    ForEach-Object { Write-Output ("  {0,-28} PID {1,-7} {2,9} MB" -f $_.ProcessName, $_.Id, [math]::Round($_.WorkingSet64 / 1MB, 0)) }
Write-Output ''
Write-Output '--- Top 10 processes by total CPU time (long-running burners) ---'
Get-Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CPU } |
    Sort-Object CPU -Descending |
    Select-Object -First 10 |
    ForEach-Object { Write-Output ("  {0,-28} PID {1,-7} {2,10} sec CPU" -f $_.ProcessName, $_.Id, [math]::Round($_.CPU, 0)) }
Write-Output ''
Write-Output '--- Top 12 processes by CPU right now (%) ---'
try {
    $cores = (Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors
    if (-not $cores -or $cores -lt 1) { $cores = 1 }
    $samples = Get-Counter '\Process(*)\% Processor Time' -SampleInterval 1 -MaxSamples 2 -ErrorAction Stop
    $samples[-1].CounterSamples |
        Where-Object { $_.InstanceName -ne '_total' -and $_.InstanceName -ne 'idle' } |
        Sort-Object CookedValue -Descending |
        Select-Object -First 12 |
        ForEach-Object { Write-Output ("  {0,-28} {1,6} %" -f $_.InstanceName, [math]::Round($_.CookedValue / $cores, 1)) }
} catch {
    Write-Output '  (live CPU sample unavailable)'
}
Write-Output ''

Write-Output '=================================================='
Write-Output ' SAFE CLEANUP (aged temp, Recycle Bin, update cache)'
Write-Output '=================================================='
$cutoff = (Get-Date).AddDays(-1)

function Clear-AgedTemp([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $items = Get-ChildItem -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt $cutoff }
    $count = @($items).Count
    $items | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    $left = @(Get-ChildItem -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt $cutoff }).Count
    Write-Output ("  {0}: {1} aged items found, {2} could not be removed (locked or admin-only)" -f $Path, $count, $left)
}

Clear-AgedTemp $env:TEMP
Clear-AgedTemp 'C:\Windows\Temp'

$wuPath = 'C:\Windows\SoftwareDistribution\Download'
if (Test-Path -LiteralPath $wuPath) {
    Get-ChildItem -LiteralPath $wuPath -Recurse -Force -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Write-Output "  $wuPath : cleared (anything left needs admin / Windows Update running)"
}

try {
    Clear-RecycleBin -Force -ErrorAction Stop
    Write-Output '  Recycle Bin: emptied'
} catch {
    Write-Output '  Recycle Bin: could not empty (may already be empty)'
}
Write-Output ''

$freeAfter = Get-FreeGB 'C'
$freed = [math]::Round($freeAfter - $freeBefore, 2)
Write-Output "C: free space AFTER: $freeAfter GB  (freed $freed GB)"
Write-Output ''
Show-LocalHealth 'AFTER'
Write-Output 'Done. Done.'
