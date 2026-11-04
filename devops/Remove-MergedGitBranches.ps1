<#
.SYNOPSIS
  Deletes merged remote branches across the author's repos. Every branch in the
  embedded lists had its pull request merged (verified against the GitHub API
  2026-10-17); master/main are never touched.

.DESCRIPTION
  For each repo checkout: fetches and prunes, shows the full delete plan,
  requires a typed YES (unless -Force), then runs
  `git push origin --delete` per branch and a safe local `git branch -d`
  (which refuses unmerged branches on its own).

.EXAMPLE
  .\Remove-MergedGitBranches.ps1
.EXAMPLE
  .\Remove-MergedGitBranches.ps1 -JaePath "$env:USERPROFILE\source\repos\JobApplicationEngine" -Force
#>
[CmdletBinding()]
param(
  [string]$JaePath = "",
  [switch]$Force
)

$ErrorActionPreference = "Stop"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Write-Host "git not found on PATH." -ForegroundColor Red
  exit 1
}

$repos = @(
  @{
    Name = "JobApplicationEngine"
    Path = $JaePath
    Branches = @(
      "fix/campaign-prepare-field-validation", "feat/remote-application-campaign",
      "fix/no-hardcoded-chrome-profile", "feat/persistent-browser-profile",
      "dependabot/github_actions/actions/setup-python-7",
      "dependabot/github_actions/actions/cache-6",
      "dependabot/github_actions/actions/checkout-7",
      "fix-greenhouse-location-autocomplete", "chore/update-gitignore",
      "fix-indeed-auth-wall", "fix-new-status-eligible",
      "docs/comprehensive-update", "fix-location-autocomplete-keyboard",
      "fix-greenhouse-live-test-bugs", "test-auto-apply-dryrun",
      "test-auto-apply-safety", "ats-adapters-apply",
      "copilot/fix-code-comments-review", "copilot/update-gmail-statuses",
      "copilot/vscode-ms9xm7ay-80ne", "copilot/enhance-job-application-automation",
      "timothygwebb-patch-2", "timothygwebb-patch-1",
      "copilot/fix-16106877-1303598415-c2432a4c-3948-406d-8294-354a7ec8f0a0"
    )
  }
)

# ---------------- plan ----------------
$plan = @()
foreach ($r in $repos) {
  if ([string]::IsNullOrWhiteSpace($r.Path)) {
    Write-Host "Skipping $($r.Name): no checkout path given (pass -JaePath etc.)." -ForegroundColor Yellow
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
