# Developer Toolkit

34 problem-resolution tools. MIT licensed.

This is not a product, and it is not a delivery of one. It is a toolkit:
scripts, utilities, and documentation for resolving problems in products
developed products — diagnose the problem, apply the fix, verify the result.
Everything here is a tool used to fix a real problem.

The automation tools post one queued article per day to a WordPress.com site you configure (see automation/SETUP.md). Example site: your-site.wordpress.com.

## Tools by problem area

- **`automation/` (5 files) — Build & publish automation.** A daily WordPress.com
  poster: one queued article a day, saved as a draft for review, via the
  WordPress.com REST API. Includes the setup guide and an example config.
  Fully standalone — needs only Python 3 and a WordPress.com OAuth token.
  Also here: a universal Swagger/OpenAPI JSON to diagram converter
  (with a sample API) — it emits Mermaid, PlantUML, or XMI, so you can diagram an API
  in free tools with no paid modeling product required.
- **`devops/` (23 files) — Version control, CI/CD & machine diagnostics.** GitHub
  Actions smoke-test workflows, merged-branch cleanup, OneDrive/machine
  diagnostics, environment validators, a base64-corruption detector,
  IIS and Certbot deployment setup, a login-page diagnostic, credential
  handling, and pipeline validation guards. Also here, in
  `devops/git-hooks/`: a pre-commit hook that blocks secrets from
  being committed in the first place, plus installers for one repo,
  for every repo, and for future clones via a git template.
- **`docs/` (3 files) — Documentation.** The writing style guide and topic calendar
  behind the daily blog series, as reusable templates, plus rate-limit
  and automation-robustness patterns.

See [CATALOG.md](CATALOG.md) for every file with a one-line description,
and every file left out with the reason.

## How to use this toolkit

Start from the problem, not the tool: run the diagnostic, read what it
proves, apply the matching patch, then verify with the build or smoke
check. The catalog describes each tool by the problem it resolves.

Run the `.ps1` scripts from Windows PowerShell 5.1. All shipped `.ps1`
files are pure ASCII, so they run cleanly under Windows PowerShell 5.1.

## What is NOT in here (on purpose)

- Not a product. Nothing here is a full delivery; each item is a tool for
  resolving a specific problem in a developed product.
- No credentials, tokens, or run state. The WordPress poster reads its
  token from a local `.wp_token` file you create yourself (see
  [automation/SETUP.md](automation/SETUP.md)); that file is never committed.
- No hardcoded machine paths. Repo locations are parameters or
  `$env:USERPROFILE` defaults — nothing here points at a specific machine.
- No unpublished drafts, personal documents, private-project source, or
  binary art. The exclusion list in CATALOG.md names each one.
- No AI-platform work. Scripts, docs, and plans for AI-platform projects
  — including any documentation of what is shipped or planned — are withheld
  entirely.
- No private game scripts. Patch and diagnostic scripts for a private
  isometric game are withheld, not reworded, under the author's
  no-potential-violation rule for public posts.

## Requirements

- Windows PowerShell 5.1 for the `.ps1` scripts (pure ASCII, no BOM issues).
- Python 3.8+ for the `.py` utilities and the WordPress poster.

## License

MIT — see [LICENSE](LICENSE).
