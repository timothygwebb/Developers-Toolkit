"""Detect (and optionally repair) base64-corrupted source files.

Some PR pushes land files as base64 text instead of raw source. The CI
symptom: C# errors CS1733/CS1002 at (1,<huge column>), or XAML error
MC3000 'Data at the root level is invalid' at (1,1).

Usage:
  python check_corruption.py [path]        scan and report (read-only)
  python check_corruption.py [path] --fix  decode corrupted files in place
                                          (keeps a .bak backup of each)
"""
import base64
import binascii
import re
import sys
from pathlib import Path

EXTS = {".cs", ".xaml", ".py", ".js", ".ts", ".tsx", ".jsx", ".json",
        ".csproj", ".sln", ".xml", ".ps1"}
SKIP_DIRS = {".git", "bin", "obj", "node_modules", "__pycache__",
             ".vs", "venv", ".venv"}
B64_RE = re.compile(r"^[A-Za-z0-9+/=\s]+$")
MIN_B64_LEN = 200


def looks_corrupt(data: bytes):
    """Return decoded text if data is base64-encoded source, else None."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None
    compact = re.sub(r"\s+", "", text)
    if len(compact) < MIN_B64_LEN:
        return None
    if not B64_RE.match(text):
        return None
    pad = (-len(compact)) % 4
    try:
        decoded = base64.b64decode(compact + ("=" * pad), validate=True)
    except (binascii.Error, ValueError):
        return None
    if len(decoded) < 50 or b"\n" not in decoded:
        return None
    try:
        dtext = decoded.decode("utf-8")
    except UnicodeDecodeError:
        return None
    markers = ("using ", "namespace ", "class ", "public ", "private ",
               "def ", "import ", "function ", "const ", "var ", "<", "{")
    if not any(m in dtext for m in markers):
        return None
    return dtext


def scan(root: Path):
    hits = []
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in EXTS:
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        try:
            data = p.read_bytes()
        except OSError:
            continue
        if len(data) > 5_000_000:
            continue
        dtext = looks_corrupt(data)
        if dtext is not None:
            hits.append((p, dtext))
    return hits


def main():
    args = sys.argv[1:]
    fix = "--fix" in args
    args = [a for a in args if a != "--fix"]
    root = Path(args[0]) if args else Path(".")
    if not root.exists():
        print(f"ERROR: path not found: {root}")
        return 2
    hits = scan(root)
    if not hits:
        print(f"OK: no base64-corrupted source files found under {root}")
        return 0
    print(f"FOUND {len(hits)} corrupted file(s) "
          f"(base64 text instead of source):")
    for p, dtext in hits:
        lines = dtext.splitlines()
        first = lines[0][:80] if lines else ""
        print(f"  !! {p}")
        print(f"     decodes to: {first}...")
        if fix:
            bak = p.with_name(p.name + ".bak")
            bak.write_bytes(p.read_bytes())
            p.write_text(dtext, encoding="utf-8")
            print(f"     fixed (backup: {bak.name})")
    if not fix:
        print()
        print("Re-run with --fix to decode them in place "
              "(keeps .bak backups).")
        return 1
    return 0


sys.exit(main())
