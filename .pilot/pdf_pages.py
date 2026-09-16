#!/usr/bin/env python3
"""Page-structured PDF text extraction (specialized for the digest index).

Unlike pdf_extract.py (which flattens pages into one text stream), this returns
page boundaries so anchors can point at the exact page a fact lives on.

Prints JSON to stdout:
    {"pages": [{"page": N, "text": "..."}, ...]}

Resolution order (no deps beyond what's present):
  1. `pdftotext` on PATH (poppler) — pages are split on the form-feed it emits.
  2. `pypdf` / `PyPDF2` (bundled copy under <script dir>/vendor) — per-page text.
If none is available, print a one-line install hint to STDERR and exit 2.

Usage:
    pdf_pages.py FILE [MAXCHARS]                 # all pages
    pdf_pages.py FILE [MAXCHARS] START [END]     # pages START..END only (1-based)
"""

import json
import os
import shutil
import subprocess
import sys

# Make bundled pypdf in <script dir>/vendor importable without PYTHONPATH.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))


def pages_pdftotext(path, start=None, end=None):
    cmd = ["pdftotext", "-q"]
    if start is not None:
        cmd += ["-f", str(start), "-l", str(end if end is not None else start)]
    cmd += [path, "-"]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if out.returncode != 0:
        return None
    # pdftotext separates pages with a form-feed character.
    pages = out.stdout.split("\f")
    while pages and not pages[-1].strip():
        pages.pop()
    return pages


def pages_pypdf(path, start=None, end=None):
    for modname in ("pypdf", "PyPDF2"):
        try:
            mod = __import__(modname)
        except Exception:
            continue
        try:
            reader = mod.PdfReader(path)
        except Exception:
            try:  # PyPDF2 old API
                reader = mod.PdfFileReader(open(path, "rb"))
            except Exception:
                continue
        idx = reader.pages
        if start is not None:
            lo = max(0, start - 1)
            hi = end if end is not None else start
            idx = idx[lo:hi]
        pages = []
        for page in idx:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                pages.append("")
        return pages
    return None


def main() -> int:
    path = sys.argv[1]
    maxchars = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    start = int(sys.argv[3]) if len(sys.argv) > 3 else None
    end = int(sys.argv[4]) if len(sys.argv) > 4 else None

    pages = None
    if shutil.which("pdftotext"):
        try:
            pages = pages_pdftotext(path, start, end)
        except Exception:
            pages = None
    if pages is None:
        pages = pages_pypdf(path, start, end)
    if pages is None:
        print(
            "pdf_pages: ingen PDF-tekstuttrekker funnet. Installer en av:\n"
            "    brew install poppler        (gir 'pdftotext')\n"
            "  eller\n"
            "    python3 -m pip install pypdf",
            file=sys.stderr,
        )
        return 2

    first = start if start is not None else 1
    out = []
    used = 0
    for i, text in enumerate(pages, first):
        if maxchars > 0 and used >= maxchars:
            break
        if maxchars > 0:
            text = text[: maxchars - used]
            used += len(text)
        out.append({"page": i, "text": text})
    json.dump({"pages": out}, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
