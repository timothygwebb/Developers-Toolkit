#Requires -Version 5.1
<#
.SYNOPSIS
    Copies the fixed pre-commit hook to the correct local structure.

.DESCRIPTION
    The hook itself is a POSIX shell script, not a PowerShell script.
    This script only copies it, byte for byte, with two destinations:

    1. INSTALL (default, primary): <RepoRoot>\.git\hooks\pre-commit
       This is the copy Git actually runs on commit. It is per-clone:
       .git\hooks is not tracked, so this copy never travels with a
       push. An existing hook is backed up first, never overwritten
       silently, and the copy is verified by SHA256 after writing.

    2. TOOLKIT COPY (default, secondary): <ToolkitRepoRoot>\hooks\pre-commit
       This is the shippable copy for the Developers-Toolkit repo.
       It is NOT committed or pushed by this script. Commit it via a
       PR, per the repo rule, after you review it.

    Source file: by default the script looks for a file named
    "pre-commit" next to this script (that is, in Downloads when you
    run both files from Downloads), then in
    $env:USERPROFILE\Downloads\pre-commit. Use -SourcePath to point
    at another copy explicitly. If no local copy is found, the
    script downloads it from GitHub (see -HookDownloadUrl) to
    Downloads\pre-commit, and only then proceeds. It never
    overwrites a local copy that already exists. Download caveat:
    the default URLs point at hooks/pre-commit in
    timothygwebb/Developers-Toolkit, which is not published yet
    and that repo is still private, so unauthenticated raw
    download will return 404 today; if it fails, place the file
    in Downloads manually. A downloaded file is only accepted if
    it is non-empty and starts with "#!/bin/sh".

    Fixed 2026-11-04: Get-Item and Get-Content now use -Force for
    .git, because .git is hidden and Get-Item without -Force does
    not return hidden items in Windows PowerShell 5.1. That bug
    made the all-repos script report real repos as FAILED with
    "Could not find item ...\.git" even though Test-Path had
    returned true for the same path.

    The source is normalized to LF line endings before copying, so a
    copy that picked up CRLF in transit does not break the shell
    script. If the source is already LF, the bytes are copied unchanged.

    The script aborts before writing anything if the source is
    missing, empty, or does not start with "#!/bin/sh".

    Defaults (staged public copy; the author's local copy uses
    his own repo as the default instead):
      RepoRoot:        the current directory. Run this script
                       from the repo checkout you want to protect,
                       or pass -RepoRoot explicitly.
      ToolkitRepoRoot: $env:USERPROFILE\source\repos\Developers-Toolkit
    Override either with a parameter. If the toolkit repo is not
    found locally, that copy is skipped with a message and the
    install copy still runs.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\Downloads\Install-PreCommitHook.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\Downloads\Install-PreCommitHook.ps1 -SourcePath $env:USERPROFILE\Downloads\pre-commit -SkipToolkit
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\Downloads\Install-PreCommitHook.ps1 -DryRun
#>

param(
    [string]$SourcePath = "",
    [string]$RepoRoot = (Get-Location).Path,
    [string]$ToolkitRepoRoot = "$env:USERPROFILE\source\repos\Developers-Toolkit",
    [string]$HookDownloadUrl = "",
    [switch]$SkipInstall,
    [switch]$SkipToolkit,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

function Fail([string]$msg) {
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit 1
}

# Script directory: $PSScriptRoot is set when run from a file.
$scriptDir = $null
if ($PSScriptRoot) {
    $scriptDir = $PSScriptRoot
} elseif ($MyInvocation.MyCommand.Path) {
    $scriptDir = Split-Path $MyInvocation.MyCommand.Path -Parent
} else {
    $scriptDir = (Get-Location).Path
}

# Resolve the source file.
if ([string]::IsNullOrWhiteSpace($SourcePath)) {
    $candidates = @(
        (Join-Path $scriptDir 'pre-commit'),
        (Join-Path "$env:USERPROFILE\Downloads" 'pre-commit')
    )
    foreach ($c in $candidates) {
        if (Test-Path -LiteralPath $c -PathType Leaf) {
            $SourcePath = $c
            break
        }
    }
    if ([string]::IsNullOrWhiteSpace($SourcePath)) {
        if ($DryRun) {
            Fail ("Source file 'pre-commit' not found, and -DryRun is set so no download will be attempted. Checked: " + ($candidates -join '; ') + ". Run without -DryRun to attempt the download, or place the pre-commit file next to this script, or pass -SourcePath.")
        }
        $downloadUrls = @()
        if (-not [string]::IsNullOrWhiteSpace($HookDownloadUrl)) {
            $downloadUrls = @($HookDownloadUrl)
        } else {
            $downloadUrls = @(
                'https://raw.githubusercontent.com/timothygwebb/Developers-Toolkit/master/hooks/pre-commit',
                'https://raw.githubusercontent.com/timothygwebb/Developers-Toolkit/toolkit/initial-package/hooks/pre-commit'
            )
        }
        Write-Host "No local pre-commit file found. Attempting download from GitHub..."
        try {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        } catch {
            Write-Host "Note: could not force TLS 1.2, continuing with the system default."
        }
        $downloadsDir = Join-Path "$env:USERPROFILE" 'Downloads'
        if (-not (Test-Path -LiteralPath $downloadsDir)) {
            New-Item -ItemType Directory -Path $downloadsDir -Force | Out-Null
        }
        $downloadPath = Join-Path $downloadsDir 'pre-commit'
        $downloaded = $false
        foreach ($url in $downloadUrls) {
            Write-Host "Trying: $url"
            try {
                Invoke-WebRequest -Uri $url -OutFile $downloadPath -UseBasicParsing -ErrorAction Stop | Out-Null
            } catch {
                Write-Host "Download failed from $url : $($_.Exception.Message)"
                Remove-Item -LiteralPath $downloadPath -Force -ErrorAction SilentlyContinue
                continue
            }
            if (-not (Test-Path -LiteralPath $downloadPath -PathType Leaf)) {
                Write-Host "Download produced no file from $url"
                continue
            }
            $downloadBytes = [System.IO.File]::ReadAllBytes($downloadPath)
            if ($downloadBytes.Length -eq 0) {
                Write-Host "Downloaded file from $url is empty, discarding it."
                Remove-Item -LiteralPath $downloadPath -Force -ErrorAction SilentlyContinue
                continue
            }
            $dlFirstEnd = [Array]::IndexOf($downloadBytes, [byte]10)
            if ($dlFirstEnd -lt 0) {
                $dlFirstEnd = $downloadBytes.Length
            }
            $dlFirstLine = [System.Text.Encoding]::ASCII.GetString($downloadBytes, 0, $dlFirstEnd).TrimEnd("`r")
            if (-not $dlFirstLine.StartsWith('#!/bin/sh')) {
                Write-Host "Downloaded file from $url does not start with '#!/bin/sh' (likely an error page), discarding it."
                Remove-Item -LiteralPath $downloadPath -Force -ErrorAction SilentlyContinue
                continue
            }
            $SourcePath = $downloadPath
            $downloaded = $true
            Write-Host "Downloaded pre-commit hook from $url to $downloadPath"
            break
        }
        if (-not $downloaded) {
            Fail ("Could not download the pre-commit hook from GitHub. Tried: " + ($downloadUrls -join '; ') + ". This is expected today: hooks/pre-commit is not yet published in Developers-Toolkit, and that repo is private, so unauthenticated raw download returns 404. Place the pre-commit file next to this script or in Downloads, pass -SourcePath, or pass -HookDownloadUrl for an already-published location.")
        }
    }
}
if (-not (Test-Path -LiteralPath $SourcePath -PathType Leaf)) {
    Fail "Source file not found: $SourcePath"
}
Write-Host "Source: $SourcePath"

$rawBytes = [System.IO.File]::ReadAllBytes($SourcePath)
if ($rawBytes.Length -eq 0) {
    Fail "Source file is empty: $SourcePath"
}

# First line must be the shell shebang.
$firstLineEnd = [Array]::IndexOf($rawBytes, [byte]10)
if ($firstLineEnd -lt 0) {
    $firstLineEnd = $rawBytes.Length
}
$firstLine = [System.Text.Encoding]::ASCII.GetString($rawBytes, 0, $firstLineEnd).TrimEnd("`r")
if (-not $firstLine.StartsWith('#!/bin/sh')) {
    Fail "Source file does not start with '#!/bin/sh'. First line was: $firstLine"
}

# Normalize CRLF (and lone CR) to LF, byte by byte. A file that is
# already LF passes through unchanged.
$converted = New-Object System.Collections.Generic.List[byte]
$i = 0
while ($i -lt $rawBytes.Length) {
    $b = $rawBytes[$i]
    if ($b -eq 13) {
        # CR: emit one LF, and skip a following LF if present.
        $converted.Add([byte]10)
        if (($i + 1) -lt $rawBytes.Length -and $rawBytes[$i + 1] -eq 10) {
            $i += 2
        } else {
            $i += 1
        }
    } else {
        $converted.Add($b)
        $i += 1
    }
}
$hookBytes = $converted.ToArray()
if ($hookBytes.Length -ne $rawBytes.Length) {
    Write-Host "Note: normalized line endings to LF (source had CRLF/CR bytes)."
}

# SHA256 of the bytes that will actually be written.
$sha = [System.Security.Cryptography.SHA256]::Create()
$hashBytes = $sha.ComputeHash($hookBytes)
$sb = New-Object System.Text.StringBuilder
foreach ($hb in $hashBytes) {
    [void]$sb.AppendFormat('{0:x2}', $hb)
}
$sourceHash = $sb.ToString()
$sha.Dispose()
Write-Host "Source SHA256: $sourceHash"

function Copy-HookFile {
    param(
        [string]$Destination,
        [string]$Label,
        [bool]$TryChmod
    )
    $parent = Split-Path $Destination -Parent
    if ($DryRun) {
        Write-Host "DRYRUN: would copy to $Label : $Destination"
        return $true
    }
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
        Write-Host "$Label : created directory $parent"
    }
    if (Test-Path -LiteralPath $Destination) {
        $existingHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Destination).Hash
        if ([string]::Equals($existingHash, $sourceHash, [StringComparison]::OrdinalIgnoreCase)) {
            Write-Host "$Label : already up to date, skipping: $Destination"
            return $true
        }
        $stamp = Get-Date -Format yyyyMMdd-HHmmss
        $backup = "$Destination.bak-$stamp"
        $n = 1
        while (Test-Path -LiteralPath $backup) {
            $backup = "$Destination.bak-$stamp-$n"
            $n += 1
        }
        Copy-Item -LiteralPath $Destination -Destination $backup -Force
        Write-Host "$Label : backed up existing file to $backup"
    }
    [System.IO.File]::WriteAllBytes($Destination, $hookBytes)
    $writtenHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Destination).Hash
    if (-not [string]::Equals($writtenHash, $sourceHash, [StringComparison]::OrdinalIgnoreCase)) {
        Fail "$Label : SHA256 mismatch after copy to $Destination (wrote $writtenHash, expected $sourceHash)"
    }
    Write-Host "$Label : copied and verified: $Destination"
    if ($TryChmod) {
        # Fixed 2026-11-04: do NOT fall back to Get-Command bash.
        # That can return WSL's bash.exe, which cannot see a
        # Windows path written as C:/Users/..., so chmod failed
        # with "No such file or directory" and, with
        # $ErrorActionPreference = 'Stop', that stderr became a
        # terminating error. chmod is best-effort only and must
        # never fail an install: the file was already written and
        # verified by SHA256 just before this step, and Git for
        # Windows normally runs the hook without a Unix bit.
        $bashPath = $null
        $gitBashCandidates = @(
            "$env:ProgramFiles\Git\bin\bash.exe",
            "$env:ProgramFiles\Git\usr\bin\bash.exe",
            "${env:ProgramFiles(x86)}\Git\bin\bash.exe",
            "$env:LOCALAPPDATA\Programs\Git\bin\bash.exe",
            "$env:LOCALAPPDATA\Programs\Git\usr\bin\bash.exe"
        )
        foreach ($candidate in $gitBashCandidates) {
            if (Test-Path -LiteralPath $candidate) {
                $bashPath = $candidate
                break
            }
        }
        if ($bashPath) {
            $unixPath = $Destination
            if ($Destination -match '^([A-Za-z]):\\(.*)$') {
                $unixPath = '/' + $matches[1].ToLower() + '/' + ($matches[2] -replace '\\', '/')
            } else {
                $unixPath = $Destination.Replace('\', '/')
            }
            $oldEAP = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            try {
                & $bashPath -c "chmod +x '$unixPath'" *> $null
                if ($LASTEXITCODE -ne 0) {
                    Write-Host "$Label : Warning: chmod +x failed (exit $LASTEXITCODE). Not fatal: the file was already written and verified."
                } else {
                    Write-Host "$Label : attempted chmod +x via Git Bash."
                }
            } catch {
                Write-Host "$Label : Warning: chmod +x could not run: $($_.Exception.Message). Not fatal: the file was already written and verified."
            } finally {
                $ErrorActionPreference = $oldEAP
            }
        } else {
            Write-Host "$Label : Git Bash not found, chmod skipped. Git for Windows normally still runs .git\hooks\pre-commit; if it does not run, run 'chmod +x .git/hooks/pre-commit' in Git Bash."
        }
    }
    return $true
}

$installFailed = $false
$copiesDone = 0

if (-not $SkipInstall) {
    $gitPath = Join-Path $RepoRoot '.git'
    if (-not (Test-Path -LiteralPath $gitPath)) {
        Write-Host "ERROR: install repo .git not found at $gitPath - skipping install copy." -ForegroundColor Red
        $installFailed = $true
    } else {
        $realGitDir = $gitPath
        if ((Get-Item -LiteralPath $gitPath -Force) -isnot [System.IO.DirectoryInfo]) {
            # Worktree / submodule: .git is a file containing "gitdir: <path>".
            # -Force is required here too: .git is hidden.
            $gitFileLine = Get-Content -LiteralPath $gitPath -TotalCount 1 -Force
            if ($gitFileLine -and $gitFileLine.StartsWith('gitdir:')) {
                $gitDirValue = $gitFileLine.Substring(7).Trim()
                if ([System.IO.Path]::IsPathRooted($gitDirValue)) {
                    $realGitDir = $gitDirValue
                } else {
                    $realGitDir = Join-Path $RepoRoot $gitDirValue
                }
            } else {
                Write-Host "ERROR: .git file at $gitPath does not contain a gitdir line - skipping install copy." -ForegroundColor Red
                $installFailed = $true
                $realGitDir = $null
            }
        }
        if ($realGitDir) {
            $hooksDir = Join-Path $realGitDir 'hooks'
            $dest = Join-Path $hooksDir 'pre-commit'
            if (Copy-HookFile -Destination $dest -Label 'INSTALL' -TryChmod $true) {
                $copiesDone += 1
            }
        }
    }
}

if (-not $SkipToolkit) {
    if (-not (Test-Path -LiteralPath $ToolkitRepoRoot)) {
        Write-Host "Toolkit repo not found at $ToolkitRepoRoot - skipping toolkit copy."
    } else {
        $toolkitHooksDir = Join-Path $ToolkitRepoRoot 'hooks'
        $toolkitDest = Join-Path $toolkitHooksDir 'pre-commit'
        if (Copy-HookFile -Destination $toolkitDest -Label 'TOOLKIT' -TryChmod $false) {
            $copiesDone += 1
            if (-not $DryRun) {
                Write-Host "TOOLKIT : this copy is NOT committed or pushed. Commit it via a PR after you review it."
            }
        }
    }
}

Write-Host ""
Write-Host "Copies completed: $copiesDone"
if ($DryRun) {
    Write-Host "Dry run only - nothing was written."
    exit 0
}
if ($installFailed -and -not $SkipInstall) {
    Fail "Install copy failed (see above). Toolkit copy, if any, is reported above."
}
if ($copiesDone -eq 0) {
    Fail "No copies were made. Check the repo paths above."
}
Write-Host "Done. Next commit in $RepoRoot will run the installed hook."
