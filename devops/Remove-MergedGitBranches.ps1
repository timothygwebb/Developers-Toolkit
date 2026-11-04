<#
.SYNOPSIS
  Deletes merged remote branches across your repos. Use this tool like this:
  edit the example $repos list below for your own repos, or drive it with
  parameters - no repo or branch list is hard-coded to a specific project.

.DESCRIPTION
  For each repo checkout: fetches and prunes, shows the full delete plan,
  requires a typed YES (unless -Force), then runs
  `git push origin --delete` per branch and a safe local `git branch -d`
  (which refuses unmerged branches on its own).

  Only delete branches whose pull requests you have verified merged.
  master/main are never touched.

.EXAMPLE
  .\Remove-MergedGitBranches.ps1
.EXAMPLE
  .\Remove-MergedGitBranches.ps1 -RepoPath "$env:USERPROFILE\source\repos\example-repo" -Branches "example-branch-1","example-branch-2" -Force
#>
[CmdletBinding()]
param(
  [Alias('JaePath')]
  [string]$RepoPath = "",
  [string[]]$Branches = @(),
  [switch]$Force
)

$ErrorActionPreference = "Stop"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Write-Host "git not found on PATH." -ForegroundColor Red
  exit 1
}

# Example driver list. Replace Name, Path, and Branches with your own repos
# and merged branches, or pass -RepoPath and -Branches instead (see below).
$repos = @(
  @{
    Name = "example-repo"
    Path = $RepoPath
    Branches = @(
      "example-branch-1", "example-branch-2",
      "dependabot/github_actions/actions/setup-python-7",
      "dependabot/github_actions/actions/cache-6",
      "dependabot/github_actions/actions/checkout-7"
    )
  }
)

# Parameter-driven mode: -RepoPath + -Branches overrides the example list.
if ($Branches.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace($RepoPath)) {
  $repos = @(
    @{
      Name = "example-repo"
      Path = $RepoPath
      Branches = $Branches
    }
  )
}

# ---------------- plan ----------------
$plan = @()
foreach ($r in $repos) {
  if ([string]::IsNullOrWhiteSpace($r.Path)) {
    Write-Host "Skipping $($r.Name): no checkout path given (pass -RepoPath)." -ForegroundColor Yellow
    continue
  }
  if (-not (Test-Path (Join-Path $r.Path ".git"))) {
    Write-Host "Skipping $($r.Name): not a git repo: $($r.Path)" -ForegroundColor Yellow
    continue
  }
  $branches = $r.Branches | Where-Object { $_ -notin @("master", "main") } | Sort-Object -Unique
  $plan += @{ Name = $r.Name; Path = $r.Path; Branches = $branches }
}

if ($plan.Count -eq 0) { Write-Host "Nothing to do."; exit 0 }

$total = ($plan | ForEach-Object { $_.Branches.Count } | Measure-Object -Sum).Sum
Write-Host ""
Write-Host "Will delete $total merged remote branches:" -ForegroundColor Cyan
foreach ($p in $plan) {
  Write-Host "  $($p.Name) ($($p.Path)): $($p.Branches.Count) branches" -ForegroundColor Cyan
}
Write-Host "master/main are never touched. Branches with unmerged PRs are excluded." -ForegroundColor Gray

if (-not $Force) {
  $answer = Read-Host "Type YES to delete these remote branches"
  if ($answer -ne "YES") { Write-Host "Aborted." -ForegroundColor Red; exit 1 }
}

# ---------------- execute ----------------
$deleted = 0; $gone = 0; $failed = 0
foreach ($p in $plan) {
  Write-Host ""
  Write-Host "--- $($p.Name) ---" -ForegroundColor Cyan
  & git -C $p.Path fetch --prune origin 2>&1 | Out-Null

  foreach ($b in $p.Branches) {
    $out = & git -C $p.Path push origin --delete $b 2>&1
    if ($LASTEXITCODE -eq 0) {
      $deleted++
      Write-Host "  deleted remote: $b" -ForegroundColor Green
    } elseif ($out -match "remote ref does not exist") {
      $gone++
      Write-Host "  already gone:   $b" -ForegroundColor Gray
    } else {
      $failed++
      Write-Host "  FAILED:         $b" -ForegroundColor Red
      $out | Select-Object -First 3 | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
    }

    # Safe local cleanup: -d refuses branches with unmerged work.
    & git -C $p.Path branch -d $b 2>&1 | Out-Null
  }
}

Write-Host ""
Write-Host "Done: $deleted deleted, $gone already gone, $failed failed." -ForegroundColor Cyan
if ($failed -gt 0) { exit 1 }
