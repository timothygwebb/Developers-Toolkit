# Git commit checker (pre-commit hook)

A pre-commit git hook that checks a commit so no secrets are submitted
to any repository in the first place. It is not a standalone secret
scanner that searches repos after the fact.

The copy Git actually runs is per-clone, in
`<repo>\.git\hooks\pre-commit`, and is never tracked or pushed.
The files in this folder are the shippable source for that copy.

## What the hook does

- Strips trailing whitespace from staged files and re-stages them,
  preserving file permissions, skipping binary and empty files, and
  adding a final newline where one is missing. A staged file inside
  an ignored directory (for example `.vscode/`) is re-staged with
  `git add -f`, but only because it was already in the staged list.
- Blocks the commit (exit 1) when a staged file contains one of
  exactly five secret patterns, corrected to POSIX extended regular
  expressions: `AKIA[0-9A-Z]{16}`, `ASIA[0-9A-Z]{16}`,
  `AIza[0-9A-Za-z_-]{35}`, `sk_live_[0-9A-Za-z]{24}`,
  `sk_test_[0-9A-Za-z]{24}`. Do not claim wider secret coverage
  than those five.
- Does NOT validate JSON by default. The original hook blocked
  commits on JSON errors and hid the real error; this version only
  validates JSON when you opt in with `VALIDATE_JSON=1 git commit`.
  That path checks that `jq` exists first (missing `jq` warns and
  skips, it does not fail) and prints `jq`'s actual parse error.

## Warnings

- Trailing whitespace is significant in Markdown: two trailing
  spaces are a hard line break. Installing this hook in a repo
  changes Markdown rendering where trailing spaces are stripped.
  That is the hook's designed behaviour, not a bug to work around
  silently.
- On Windows, `chmod +x` is best-effort only. Git for Windows
  normally runs `.git\hooks\pre-commit` without a Unix executable
  bit when `core.fileMode` is false (the Windows default), so a
  chmod failure must never be treated as a failed install. The
  installers below already treat it that way.

## Install into one repo

Run, from Windows PowerShell 5.1:

    powershell -ExecutionPolicy Bypass -File Install-PreCommitHook.ps1

Defaults: install to the repo in the current directory (run it
from a repo checkout, or pass `-RepoRoot`), and copy a
shippable copy to
`$env:USERPROFILE\source\repos\Developers-Toolkit\hooks\pre-commit`.
Use `-SkipInstall` / `-SkipToolkit` / `-DryRun` / `-SourcePath`
to change that. The script commits and pushes nothing; the
toolkit copy still needs a pull request.

## Install into every repo, plus future clones

Run, from Windows PowerShell 5.1:

    powershell -ExecutionPolicy Bypass -File Install-PreCommitHookAllRepos.ps1

"Every repo" means every immediate subdirectory of
`$env:USERPROFILE\source\repos` (or `-ReposRoot`) containing a
`.git` directory or file. It is not recursive and it does not
touch bare repos. Existing custom hooks are skipped by default
and listed; use `-Force` to replace one (the old hook is backed
up first). Use `-Exclude` for repo names to skip, and `-DryRun`
to see what would happen without writing anything.

With `-InitNonRepos`, a folder with no `.git` is initialized
with `git init` first, then gets the hook the same way as any
other repo. Without it, a non-repo is skipped, as before.
Nothing is staged or committed by init, and deleting the new
`.git` folder undoes it. A folder that looks like a tool
folder or a Python virtual environment (any hidden
dot-folder such as `.vs`, or named `venv` or `env`, or
containing `pyvenv.cfg`) is never initialized, even with
`-InitNonRepos`, and a folder passed with `-Exclude` is never
initialized either. `-InitNonRepos` is opt-in, not the
default, because initializing a folder is a new repo, not
just a hook copy.

The same script also sets up future clones by default, unless
`-SkipTemplate` is given:

- Copies the hook to `$env:USERPROFILE\.git-templates\hooks\pre-commit`
  (or `-TemplateDir`), with the same backup, custom-hook skip,
  and SHA256 verification as a repo copy.
- Sets `git config --global init.templateDir` to that directory,
  and verifies it by reading it back. If a different template
  directory is already set and that directory exists, the script
  keeps that setting and copies the hook into that template
  instead; it does not overwrite global config silently.
- Verifies with a throwaway `git init` in a temp folder, checks
  `.git\hooks\pre-commit` there with the correct SHA256, then
  deletes the temp folder.

A template does NOT change existing clones, and re-running
`git init` in an existing repo does not overwrite an existing
hook. The template is a copy, not a link: later hook changes
require re-running the installer for both existing clones and
the template. Undo the template with
`git config --global --unset init.templateDir`, plus optionally
deleting the template folder.

## Download if no local copy exists

Both installers, only when no local `pre-commit` copy exists
and never in `-DryRun`, try to download the hook from the
Developers-Toolkit repo on GitHub (master first, then the
toolkit branch), accepting a download only if it is non-empty
and starts with `#!/bin/sh`. Until this hook is published in
that repo, that download will fail and the script stops clearly;
place the `pre-commit` file beside the installer and run again.
Do not let a failed or HTML download leave a partial file in
place: the installers delete partial and bad downloads.

## Provenance

The hook was fixed from a real failure, not written from
scratch: the original secret patterns never matched under
`grep -E` (`\{16\}` is not an extended-regular-expression
interval), and the original scanner's piped `while` loop ran
in a subshell, so its `exit 1` could never block a commit.
The fixed version was tested in a scratch git repo: a clean
commit passes, staged AKIA / `sk_test_` / AIza secrets block
with exit 1, trailing whitespace is stripped and re-staged
(including a filename with a space), binary files are left
untouched, invalid JSON passes by default and blocks with the
real `jq` error when opted in, and a tracked file inside an
ignored `.vscode/` directory is stripped with no warning.
