# Catalog

Every file in this toolkit, with a one-line description, and every file
left out, with the reason. Each entry is a problem-resolution tool, not a
product component. Staged 2026-10-30.

## Included files

### automation/ (5 files)

- `automation/config.example.json` — Example config for the poster: site + draft/publish status (copy to config.json).
- `automation/post_article.py` — Post the next queued article to a WordPress.com site configured in config.json via the WordPress.com REST API. Example site: your-site.wordpress.com.
- `automation/SETUP.md` — Setup guide for the WordPress poster: queue format, token acquisition, daily scheduling, failure behavior. Use it like this: configure a site, queue articles, run once a day.
- `automation/Convert-SwaggerToDiagrams.py` — Convert Swagger 2.0 / OpenAPI 3.x JSON to diagrams in free, open formats (Mermaid, PlantUML, XMI): schemas become classes, paths become interfaces grouped by tag.
- `automation/Sample-Swagger.json` — Sample OpenAPI 3 spec (pet store) to test the converter.

### devops/ (15 files)

- `devops/Check-OneDriveAndRam.ps1` — Follow-up to Diagnose-And-Clean-Machine.ps1:
- `devops/Diagnose-And-Clean-Machine.ps1` — 1) Shows CPU / RAM / disk before cleanup
- `devops/Extract-ResumeText.py` — Extract resume text from a PDF using the repo's own pypdf dependency.
- `devops/Remove-MergedGitBranches.ps1` — Deletes merged remote branches. Variablized driver: pass -RepoPath and -Branches, or edit the example list in the script. Example repo: example-repo. Master/main are never touched.
- `devops/Reset-OneDriveSync.ps1` —  (v2) v2 fixes v1: (a) the sampler printed with Write-Output while also
- `devops/Test-OneDriveSyncProbe.ps1` — Answers two questions left open by Reset-OneDriveSync.ps1:
- `devops/check-js-mirrors.yml` — GitHub Actions workflow: check-js-mirrors
- `devops/check_corruption.py` — Detect (and optionally repair) base64-corrupted source files.
- `devops/fix_env_keys.py` — Rename mis-prefixed .env keys to the APP_* names the engine actually reads.
- `devops/validate_env.py` — Validate a project .env without exposing secret values.
- `devops/configure_iis.ps1` — IIS reverse-proxy setup with Server/Desktop detection and a fallback when ARR/URL Rewrite are missing.
- `devops/automate_certbot_setup.py` — Certbot automation that validates every config value up front and fails fast on placeholders.
- `devops/diagnose_linkedin_login.py` — LinkedIn login-page diagnostic: proves the full login page loaded by checking for the password Show/Hide toggle. Verified with py_compile.
- `devops/secure_credentials.py` — Credential storage via Windows Credential Manager, commands run as argument lists with shell=False.
- `devops/pipeline_validate.py` — Guards a jobs CSV against its tracker workbook: row counts plus required-column checks.

### devops/git-hooks/ (4 files)

- `devops/git-hooks/pre-commit` — Git commit checker: a pre-commit hook that strips trailing whitespace from staged files and blocks the commit when a staged file contains one of five secret patterns (AKIA, ASIA, AIza, sk_live_, sk_test_). JSON validation is off by default, opt in with VALIDATE_JSON=1.
- `devops/git-hooks/Install-PreCommitHook.ps1` — Install the hook into one repo (default: the current directory repo, or -RepoRoot) and copy a shippable copy to Developers-Toolkit/hooks/pre-commit. Pure ASCII, Windows PowerShell 5.1; commits and pushes nothing.
- `devops/git-hooks/Install-PreCommitHookAllRepos.ps1` — Install the hook into every immediate subdirectory of the repos root containing .git (custom hooks skipped by default, listed, -Force to replace with backup), and set up a git template directory so future clones get the hook. Pure ASCII, Windows PowerShell 5.1.
- `devops/git-hooks/README.md` — How the hook works, what it blocks, the Markdown trailing-space warning, the one-repo and all-repos installers, the future-clone template, and the download-if-missing behaviour.

### devops/ci-workflows/ (4 files)

- `devops/ci-workflows/python-playwright-smoke.yml` — GitHub Actions workflow: Python + Playwright smoke test template
- `devops/ci-workflows/python-pytest-smoke.yml` — GitHub Actions workflow: Python pytest smoke test template
- `devops/ci-workflows/python-pytest-tests-smoke.yml` — GitHub Actions workflow: Python tests smoke test template
- `devops/ci-workflows/python-compile-smoke.yml` — GitHub Actions workflow: Python compile smoke test template

### docs/ (3 files)

- `docs/STYLE_GUIDE.md` — Writing style guide template for a daily WordPress poster: voice, honesty rules, availability CTA template with placeholders. Example site: your-site.wordpress.com.
- `docs/TOPICS.md` — 30-day topic calendar template with generic example topics. Replace the examples with your own topics.
- `docs/RATE_LIMITING_FIX.md` — Rate-limit and Playwright robustness patterns: pacing, retries, explicit waits, submit reliability.

## Notes on shipped files

- `README.md` — toolkit overview, layers, and the patch-script safety pattern (written for this staging).
- `LICENSE` — MIT license text.
- `automation/SETUP.md` — setup guide for the WordPress poster (see automation/ entry above).

- `devops/Extract-ResumeText.py` extracts resume text from a PDF you point it at. The `docs/` guides are templates — replace placeholders with your own site and voice.

## Excluded files (from the source folders) and reasons

- Game patch and diagnostic scripts for a private isometric game (112 files, plus a smoke workflow and a sandbox diagnostic for the same game) — withheld under the author's no-potential-violation rule for public posts (2026-11-04): the scripts handle third-party retail scenario formats, so they are not published here, and they are not reworded to another project name, because rewording would leave that handling in place.

- `365ITGuard-hash-mismatch-report.txt` — Beta-test report, not tooling; machine-specific.
- Personal email-rules document with account details — withheld.
- Personal family note — withheld.
- Superseded build script — Superseded by the pick-loop design; do not run.
- AI-platform scripts, installers, probe/design docs, plan docs, and source fragments — withheld: AI-platform work, including any documentation of what is shipped or planned, is not published publicly.
- `agent-platform/` (51 AI-platform scripts) and the AI-platform smoke-test workflow — withheld under the same rule.
- `Invoke-BetaInstall-365ITGuard.ps1` — Harness for a closed third-party beta; downloads/runs a third-party installer with a hash-mismatch history. Not reusable public tooling.
- `cli-sync-real.py` — Real-Atlassian sync design. Superseded by the mock design.
- `cli-with-real-sync.py` — Real-Atlassian sync design, plus a proprietary / All Rights Reserved header.
- `cli-with-mock-sync.py` — Correct mock design, but the header marks it proprietary / All Rights Reserved. Needs a license decision before any public release.
- `time_tracker.py` — Same proprietary / All Rights Reserved header. Needs a license decision before any public release.
- `proactive_messages/ (81 files)` — Agent working state, not tooling.
- `__pycache__/ (7 files)` — Compiled Python bytecode.
- `king-art/` — Binary PNG art.
- Personal resume documents — withheld.
- Private game source files — Source of the private game (intended for commercial sale).
- `tsx-help-assistant-fill-popout/` — Empty directory; nothing to ship.
- `blog-automation/.wp_token` — Live WordPress.com OAuth token. Never shipped.
- `blog-automation/state.json` — Run state (post IDs/URLs).
- `blog-automation/queue/, posted/` — Article drafts; unpublished drafts stay private.
- `blog-automation/config.json` — Replaced by automation/config.example.json (site name replaced with an example site in the example).
