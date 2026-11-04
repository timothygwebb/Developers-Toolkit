"""Validate a project .env without exposing secret values."""
import re
from pathlib import Path

p = Path(".env")
if not p.exists():
    print("ERROR: .env not found in current directory")
    raise SystemExit(1)

vals = {}
malformed_lines = []
raw_lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
for lineno, line in enumerate(raw_lines, start=1):
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        continue
    k, v = stripped.split("=", 1)
    k = k.strip()
    v = v.strip()
    # dotenv-compatible checks: balanced quotes, no nested quotes inside quoted values
    if (v.startswith('"') and not (v.endswith('"') and v.count('"') == 2)) or \
       (v.startswith("'") and not (v.endswith("'") and v.count("'") == 2)):
        malformed_lines.append((lineno, k, "unbalanced or nested quotes"))
    elif not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', k):
        malformed_lines.append((lineno, k, "invalid key name"))
    else:
        vals[k] = v.strip("\"'")

if malformed_lines:
    print("== MALFORMED LINES (python-dotenv will skip these) ==")
    for lineno, k, reason in malformed_lines:
        print(f"  !! line {lineno}: {k} — {reason}")
    print()

def mask(v):
    return "(empty)" if not v else f"(set, {len(v)} chars)"

def check_bool(k):
    v = vals.get(k, "")
    if v and v.lower() not in ("true", "false"):
        print(f"  WARN {k}: should be true/false")

def check_int(k, lo=None, hi=None):
    v = vals.get(k, "")
    if v:
        try:
            n = int(v)
            if (lo is not None and n < lo) or (hi is not None and n > hi):
                print(f"  WARN {k}: value {n} outside expected range [{lo},{hi}]")
        except ValueError:
            print(f"  WARN {k}: not an integer")

print("== Personal info (required for form filling) ==")
for k in ["APP_FULL_NAME", "APP_EMAIL", "APP_PHONE", "APP_LINKEDIN", "APP_GITHUB", "APP_LOCATION"]:
    v = vals.get(k, "")
    print(f"  [{'OK  ' if v else 'MISS'}] {k} {mask(v)}")
    if k == "APP_EMAIL" and v and "@" not in v:
        print("    WARN: doesn't look like an email address")
    if k in ("APP_LINKEDIN", "APP_GITHUB") and v and not v.startswith("http"):
        print("    WARN: doesn't look like a URL")

print("== Automation behavior ==")
for k in ["AUTO_APPLY_ENABLED", "APP_HEADLESS"]:
    v = vals.get(k, "")
    print(f"  [{'OK  ' if v else 'MISS'}] {k} = {v.lower() if v else '(empty, uses default)'}")
    check_bool(k)
for k, lo, hi in [("APP_MAX_PER_HOUR", 1, 50), ("APP_MAX_PER_DAY", 1, 200),
                  ("APP_SLOW_MO", 0, 2000), ("APP_PAGE_LOAD_TIMEOUT", 5000, 120000),
                  ("APP_ACTION_TIMEOUT", 1000, 60000), ("APP_DELAY_BETWEEN_JOBS", 0, 600),
                  ("APP_MAX_RETRIES", 0, 10)]:
    v = vals.get(k, "")
    print(f"  [{'OK  ' if v else 'dflt'}] {k} = {v if v else '(default)'}")
    check_int(k, lo, hi)

print("== Gmail sync (optional) ==")
for k in ["GMAIL_ADDRESS", "GMAIL_APP_PASSWORD"]:
    print(f"  [{'OK  ' if vals.get(k) else 'MISS'}] {k} {mask(vals.get(k, ''))}")

print("== M365 sync (optional) ==")
for k in ["MS_GRAPH_ACCESS_TOKEN", "ONEDRIVE_job_tracker_path", "OUTLOOK_STATUS_WINDOW_DAYS"]:
    v = vals.get(k, "")
    print(f"  [{'OK  ' if v else 'MISS'}] {k} {mask(v)}")
check_int("OUTLOOK_STATUS_WINDOW_DAYS", 1, 90)

print("== Unknown keys (possible typos) ==")
known = {"APP_FULL_NAME", "APP_EMAIL", "APP_PHONE", "APP_LINKEDIN", "APP_GITHUB", "APP_LOCATION",
         "GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "AUTO_APPLY_ENABLED", "APP_HEADLESS",
         "APP_SLOW_MO", "APP_PAGE_LOAD_TIMEOUT", "APP_ACTION_TIMEOUT", "APP_MAX_RETRIES",
         "APP_MAX_PER_HOUR", "APP_MAX_PER_DAY", "APP_DELAY_BETWEEN_JOBS",
         "MS_GRAPH_ACCESS_TOKEN", "ONEDRIVE_job_tracker_path", "OUTLOOK_STATUS_WINDOW_DAYS",
         "JOB_TRACKER_SPREADSHEET", "JOB_TRACKER_SHEET_NAME", "JOBS_CSV", "CI",
         "PYTHONUNBUFFERED", "PIP_DISABLE_PIP_VERSION_CHECK"}
unknown = [k for k in vals if k not in known]
if unknown:
    for k in unknown:
        print(f"  ? {k} {mask(vals[k])}")
else:
    print("  (none)")

print("done")
