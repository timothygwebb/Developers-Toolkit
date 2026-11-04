"""Rename mis-prefixed .env keys to the APP_* names the engine actually reads."""
from pathlib import Path

p = Path(".env")
t = p.read_text(encoding="utf-8")

fixes = [
    ("DELAY_BETWEEN_JOBS=", "APP_DELAY_BETWEEN_JOBS="),
    ("PAGE_LOAD_TIMEOUT=", "APP_PAGE_LOAD_TIMEOUT="),
    ("ACTION_TIMEOUT=", "APP_ACTION_TIMEOUT="),
    ("SLOW_MO=", "APP_SLOW_MO="),
    ("MAX_RETRIES=", "APP_MAX_RETRIES="),
    ("MAX_APPLICATIONS_PER_HOUR=", "APP_MAX_PER_HOUR="),
    ("MAX_APPLICATIONS_PER_DAY=", "APP_MAX_PER_DAY="),
]

# guard: don't double-prefix if APP_ version already present
for old, new in fixes:
    if old in t and new not in t:
        t = t.replace(old, new)
        print(f"renamed {old.rstrip('=')} -> {new.rstrip('=')}")
    elif new in t:
        print(f"already OK: {new.rstrip('=')}")

# lowercase 'headless=' -> 'APP_HEADLESS=' (only if APP_HEADLESS not present)
if "APP_HEADLESS=" not in t and "\nheadless=" in t:
    t = t.replace("\nheadless=", "\nAPP_HEADLESS=")
    print("renamed headless -> APP_HEADLESS")

p.write_text(t, encoding="utf-8")
print("done")
