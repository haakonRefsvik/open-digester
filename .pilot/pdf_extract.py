#!/usr/bin/env python3
"""Extract text from a PDF, stdout-only, no dependencies beyond what's present.

Resolution order:
  1. binary `pdftotext` on PATH (poppler)
  2. python `pypdf`
  3. python `PyPDF2`
If none is available, print a one-line install hint to STDERR and exit 2.
"""
import os, sys

# Make bundled pypdf in <script dir>/vendor importable without PYTHONPATH.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

def main() -> int:
    path = sys.argv[1]
    maxchars = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    # 1) poppler's pdftotext binary
    import shutil, subprocess
    if shutil.which("pdftotext"):
        try:
            out = subprocess.run(
                ["pdftotext", "-q", path, "-"],
                capture_output=True, text=True, timeout=300,
            )
        except Exception as e:
            print(f"pdf_extract: pdftotext failed: {e}", file=sys.stderr)
        else:
            if out.returncode == 0:
                text = out.stdout
                if maxchars > 0:
                    text = text[:maxchars]
                sys.stdout.write(text)
                return 0
            print("pdf_extract: pdftotext exited %s" % out.returncode, file=sys.stderr)

    # 2) pypdf / PyPDF2
    text = None
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
        pages = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                continue
        text = "\n".join(pages)
        break
    if text is None:
        print(
            "pdf_extract: ingen PDF-tekstuttrekker funnet. Installer en av:\n"
            "    brew install poppler        (gir 'pdftotext')\n"
            "  eller\n"
            "    python3 -m pip install pypdf",
            file=sys.stderr,
        )
        return 2
    if maxchars > 0:
        text = text[:maxchars]
    sys.stdout.write(text)
    return 0

if __name__ == "__main__":
    sys.exit(main())
