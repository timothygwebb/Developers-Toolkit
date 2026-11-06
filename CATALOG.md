# Catalog

Every file in this toolkit, with a one-line description. Each entry is a problem-resolution tool, not a
product component. Staged 2026-10-30.

## Included files

### automation/ (5 files)

- `automation/config.example.json` — Example config for the poster: site + draft/publish status (copy to config.json).
- `automation/post_article.py` — Post the next queued article to a WordPress.com site configured in config.json via the WordPress.com REST API. Example site: your-site.wordpress.com.
- `automation/SETUP.md` — Setup guide for the WordPress poster: queue format, token acquisition, daily scheduling, failure behavior. Use it like this: configure a site, queue articles, run once a day.
- `automation/Convert-SwaggerToDiagrams.py` — Convert Swagger 2.0 / OpenAPI 3.x JSON to diagrams in free, open formats (Mermaid, PlantUML, XMI, editable Visio .vsdx; reads a file or a URL): schemas become classes, paths become interfaces grouped by tag. Validated: the .vsdx opens as editable shapes.
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

