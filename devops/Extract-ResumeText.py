"""Extract resume text from a PDF using the repo's own pypdf dependency.

Replaces the `pdftotext` step in docs/REMOTE_CAMPAIGN.md. Extracts directly
from the PDF you point it at, so the source-text hash still means something.

Usage (run from your JobApplicationEngine clone):
    python Extract-ResumeText.py "C:\\path\\to\\resume.pdf"

Writes .application-private\\source-resume.txt next to the repo.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    sys.exit("pypdf is not installed. Run: pip install \"pypdf>=6.14.2\"")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(f"Usage: {Path(sys.argv[0]).name} <resume.pdf>")
    pdf = Path(sys.argv[1])
    if not pdf.is_file() or not pdf.read_bytes().startswith(b"%PDF-"):
        sys.exit(f"Not a PDF file: {pdf}")
    reader = PdfReader(str(pdf))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    text = "\n\n".join(p for p in pages if p).strip()
    if len(text) < 200:
        sys.exit(
            f"Only {len(text)} characters extracted; the PDF may be scanned "
            "images. If so, run it through OCR first, then retry."
        )
    out = Path(".application-private") / "source-resume.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(text)} characters, {len(pages)} pages)")


if __name__ == "__main__":
    main()
