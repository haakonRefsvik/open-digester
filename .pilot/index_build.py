#!/usr/bin/env python3
"""Eager workspace digest index — build a persistent `.dsh/digest/` index.

The idea (vs. on-demand `digest.sh`): pay the expensive prefill ONCE, in the
background, at workspace init, and store the *result* as small per-file "cards"
so the real model can look up a file without ever pre-filling the raw bytes.

Three tiers, in one index:
  1. Structural anchors — no LLM, deterministic, always built:
     section headers, identifiers (#define / assignment / def / class /
     register), hex addresses (0x...), and value+unit tokens (0,1 ml).
  2. Eager summary — optional LLM brief for big docs/logs (--summarize),
     produced through the same digest_call.py material path as digest.sh.
  3. Focused digest — NOT here; still digest.sh, but now the material is
     already cached by prewarm.py and the index tells you *where* to look.

Key correctness property: every card is keyed by the file's content hash
(sha256). `lookup` re-hashes the file and refuses a card whose hash no longer
matches, so an edited file can never be answered from a stale summary.

Layout under OUTDIR (default .dsh/digest/):
    index.json            manifest: root, policy, per-file {fingerprint, card, …}
    cards/<sha256path>.json   one card per file (path-hashed → overwritten in place)
    run.log               optional daemon log (written by digest_index.sh)

Subcommands:
    build  ROOT OUTDIR [--summarize] [--force] [--max-files N] [--max-bytes N]
    lookup ROOT OUTDIR PATH [--json]
    status ROOT OUTDIR
    clean  OUTDIR
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

PILOT = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- selection --
# Directories we never index (the index itself, caches, VCS, deps, build output).
EXCLUDE_DIRS = {
    ".git", ".hg", ".svn", ".pilot", ".dsh", ".venv", "venv", "node_modules",
    "vendor", "__pycache__", ".mypy_cache", ".pytest_cache", "dist", "build",
    "target", ".next", ".cache", ".DS_Store",
}
EXCLUDE_NAMES = {".DS_Store", "Thumbs.db"}
# Text-ish extensions we accept eagerly even if `file` is ambiguous.
TEXT_EXTS = {
    ".c", ".h", ".cpp", ".hpp", ".cc", ".ino", ".py", ".js", ".ts", ".tsx",
    ".jsx", ".mjs", ".cjs", ".rs", ".go", ".java", ".kt", ".swift", ".rb",
    ".sh", ".bash", ".zsh", ".md", ".txt", ".log", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".conf", ".xml", ".html", ".css", ".scss",
    ".sql", ".csv", ".tsv", ".proto", ".graphql", ".env", ".make", ".mk",
}
PDF_EXT = ".pdf"

DEFAULT_MAX_FILES = 500
DEFAULT_MAX_BYTES = 2_000_000   # 2 MB per file
DEFAULT_ANCHOR_CHARS = 200_000  # how much text to scan for anchors per file
DEFAULT_SUMMARIZE_MIN_BYTES = 40_000  # only LLM-summarize files this big
DEFAULT_SUMMARY_TOKENS = 400        # per-chunk brief length
DEFAULT_CHUNK_TOKENS = 60000        # target chunk size (fits ~65k context)
DEFAULT_OVERLAP_TOKENS = 2000       # tail overlap between chunks
DEFAULT_CHARS_PER_TOKEN = 3.0       # conservative chars/token (math-heavy text is ~3.0)

# ------------------------------------------------------------------ helpers --
def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fingerprint(data: bytes) -> str:
    return "sha256:" + sha256_hex(data)


def read_bytes(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def is_binary(path: str) -> bool:
    """Null-byte sniff first (fast), then `file` fallback (authoritative)."""
    with open(path, "rb") as fh:
        head = fh.read(8192)
    if b"\x00" in head:
        return True
    try:
        out = subprocess.run(
            ["file", "-b", path], capture_output=True, text=True, timeout=10
        )
        if out.returncode == 0:
            low = out.stdout.lower()
            return any(
                k in low
                for k in ("executable", "binary", "image", "archive", "compressed")
            )
    except Exception:
        pass
    return False


def is_candidate(relpath: str, path: str, max_bytes: int) -> bool:
    name = os.path.basename(relpath)
    if name in EXCLUDE_NAMES:
        return False
    if os.path.getsize(path) > max_bytes:
        return False
    ext = os.path.splitext(relpath)[1].lower()
    if ext == PDF_EXT:
        return True
    if ext in TEXT_EXTS:
        return True
    # Unknown extension: accept only if it is plausibly text.
    return not is_binary(path)


def iter_files(root: str, outdir: str, max_files: int, max_bytes: int):
    """Yield (relpath, abspath) for candidate files, newest-first by size desc."""
    out_abs = os.path.abspath(outdir)
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames if d not in EXCLUDE_DIRS
            and os.path.abspath(os.path.join(dirpath, d)) != out_abs
        )
        for fn in sorted(filenames):
            abs_p = os.path.join(dirpath, fn)
            rel = os.path.relpath(abs_p, root)
            if not is_candidate(rel, abs_p, max_bytes):
                continue
            hits.append((rel, abs_p))
            if len(hits) >= max_files:
                break
        if len(hits) >= max_files:
            break
    # Big files first: they're the ones the index exists to help with.
    hits.sort(key=lambda t: (-os.path.getsize(t[1]), t[0]))
    return hits[:max_files]


# ----------------------------------------------------------- anchor extract --
_HEADING = re.compile(r"^#{1,6}\s+\S")
_SECTION = re.compile(r"^\s*(\d+(?:\.\d+)+)\s+(\S.*)$")
_DEFINE = re.compile(r"#\s*define\s+([A-Za-z_]\w*)")
_ASSIGN = re.compile(r"^\s*([A-Za-z_]\w*)\s*=\s*[^=]")
_DEFN = re.compile(r"\b(def|class|struct|enum|interface|fn|fun|function|sub)\s+([A-Za-z_]\w*)")
_REGISTER = re.compile(r"\b(REGISTER|Register)\s+([A-Za-z_][\w.]*)")
_HEX = re.compile(r"\b0x[0-9a-fA-F]{2,}\b")
_UNIT = re.compile(r"\b\d+[.,]\d+\s*(?:ml|mL|l|L/min|°C|hPa|kPa|bar|V|A|W|Hz|s)\b")


def classify_line(st: str):
    """Return [(kind, value), ...] anchors for one stripped line. Shared by
    both the generic text path and the PDF per-page path."""
    out = []
    if _HEADING.match(st):
        out.append(("header", st))
    m = _SECTION.match(st)
    if m and len(st) <= 80 and re.search(r"[A-Za-zÅÆØåæø]", m.group(2)):
        out.append(("section", st))
    if len(st) <= 80 and st.isupper() and re.search(r"[A-ZÅÆØ]", st) and re.search(r"\w", st):
        out.append(("header", st))
    for mm in _DEFINE.finditer(st):
        out.append(("define", mm.group(1)))
    for mm in _ASSIGN.finditer(st):
        out.append(("assign", mm.group(1)))
    for mm in _DEFN.finditer(st):
        out.append(("def", mm.group(2)))
    for mm in _REGISTER.finditer(st):
        out.append(("register", mm.group(2)))
    for mm in _HEX.finditer(st):
        out.append(("hex", mm.group(0)))
    for mm in _UNIT.finditer(st):
        out.append(("unit", mm.group(0)))
    return out


def extract_anchors(text: str, cap: int) -> list:
    """Deterministic, LLM-free anchors for plain text (no page info)."""
    anchors = []
    seen = set()
    for line in text.splitlines()[:200_000]:
        st = line.strip()
        if not st:
            continue
        for kind, value in classify_line(st):
            value = value.strip()
            if not value or len(value) > 120:
                continue
            key = (kind, value)
            if key in seen:
                continue
            seen.add(key)
            anchors.append({"type": kind, "text": value})
            if len(anchors) >= cap:
                return anchors
    return anchors


def pdf_pages(path: str, maxchars: int) -> list:
    """Page-structured text: [{page, text}, ...] via pdf_pages.py."""
    out = subprocess.run(
        [sys.executable, os.path.join(PILOT, "pdf_pages.py"), path, str(maxchars)],
        capture_output=True, text=True, timeout=320,
    )
    if out.returncode != 0:
        return []
    try:
        return json.loads(out.stdout).get("pages", [])
    except Exception:
        return []


def pdf_slice(path: str, start: int, end: int, maxchars: int = 0) -> str:
    """Extract ONLY pages [start, end] (1-based, inclusive) as plain text."""
    out = subprocess.run(
        [sys.executable, os.path.join(PILOT, "pdf_pages.py"), path, str(maxchars),
         str(start), str(end)],
        capture_output=True, text=True, timeout=320,
    )
    if out.returncode != 0:
        return ""
    try:
        return "\n".join(p["text"] for p in json.loads(out.stdout).get("pages", []))
    except Exception:
        return ""


def _page_label(lines):
    """First heading-like line, else first non-empty line."""
    label = ""
    for st in (ln.strip() for ln in lines):
        if not st:
            continue
        if (
            _HEADING.match(st)
            or _SECTION.match(st)
            or (len(st) <= 80 and st.isupper() and re.search(r"[A-ZÅÆØ]", st))
        ):
            label = st
            break
    if not label:
        for st in (ln.strip() for ln in lines):
            if st:
                label = st
                break
    return label


def extract_pdf_anchors(pages: list, cap: int = 400):
    """PDF-specialized anchors.

    Two guarantees:
      * `pageIndex` always covers EVERY page (a table of contents for jumping).
      * `anchors` are capped at `cap`, with structural types (header/section)
        collected first so the budget isn't flooded by formula/word noise in
        math-heavy prose before the back half of the document is reached.
    """
    n_pages = len(pages)
    # 1) Full page index — never truncated by the anchor budget.
    page_index = []
    for pg in pages:
        page_index.append({"page": pg["page"], "label": _page_label(pg["text"].splitlines())})

    # 2) Capped anchors, structural types first.
    anchors = []
    seen = set()

    def scan(types):
        for pg in pages:
            pageno = pg["page"]
            for line in pg["text"].splitlines():
                st = line.strip()
                if not st:
                    continue
                for kind, value in classify_line(st):
                    if kind not in types:
                        continue
                    value = value.strip()
                    if not value or len(value) > 120:
                        continue
                    key = (kind, value, pageno)
                    if key in seen:
                        continue
                    seen.add(key)
                    anchors.append({"type": kind, "text": value, "page": pageno})
                    if len(anchors) >= cap:
                        return

    scan(("header", "section"))
    if len(anchors) < cap:
        scan(("define", "register", "hex", "unit", "def", "assign"))
    return anchors, page_index, n_pages


# --------------------------------------------------------------- summarize --
def llm_brief(material: str, tokens: int, sysprompt: str = "") -> str:
    """One brief through digest_call.py. Returns '' on fail."""
    if not material.strip():
        return ""
    env = dict(os.environ)
    env.update({
        "MODEL": os.environ.get("DIGEST_MODEL", "qwen3.5:2b-mlx"),
        "TOKENS": str(tokens),
        "FOCUS": "",
        "THINK": "0",
        "TIMEOUT": os.environ.get("DIGEST_TIMEOUT", "120"),
        "NUM_CTX": os.environ.get("DIGEST_NUM_CTX", "65536"),
        "KEEP_ALIVE": os.environ.get("DIGEST_KEEP_ALIVE", "30m"),
        "OLLAMA_URL": os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"),
        "DIGEST_SYSPROMPT": sysprompt,
    })
    try:
        p = subprocess.run(
            [sys.executable, os.path.join(PILOT, "digest_call.py")],
            input=material, capture_output=True, text=True, env=env,
            timeout=int(env["TIMEOUT"]) + 5,
        )
    except Exception:
        return ""
    if p.returncode != 0:
        return ""
    return (p.stdout or "").strip()


def summarize(path: str, cap: int, tokens: int):
    """Whole-file eager brief (text files). Returns '' on fail."""
    mat = subprocess.run(
        [sys.executable, os.path.join(PILOT, "prewarm.py"), "material", path, str(cap)],
        capture_output=True, text=True, timeout=60,
    )
    material = mat.stdout if mat.returncode == 0 else ""
    return llm_brief(material, tokens)


# ------------------------------------- map-reduce chunk summarize (PDF, LLM-only) --
CHUNK_SYSPROMPT = (
    "You are tagging ONE chunk of a larger document for a retrieval index. "
    "List, in at most {tokens} tokens, the main topics, concepts, keywords, and anything "
    "a reader might search for in this chunk. Approximate wording is fine — your job is "
    "to tell a reader WHAT is roughly here, not to reproduce it exactly. Use short "
    "bullets. No preamble, no meta commentary."
)


def chunk_text(text: str, chunk_chars: int, overlap_chars: int) -> list:
    """Split text into [start, end) char windows with tail overlap. Structure-agnostic."""
    chunks = []
    start = 0
    n = len(text)
    i = 0
    while start < n:
        end = min(start + chunk_chars, n)
        chunks.append({"i": i, "start": start, "end": end, "text": text[start:end]})
        if end >= n:
            break
        start = end - overlap_chars
        i += 1
    return chunks


def tokenize(text, model, url=None):
    """Exact token count via /api/chat with num_predict=0 (real tokenizer).

    Returns the prompt_eval_count (int), or -1 if the tokenizer is unavailable.
    NOTE: this is a full prompt-eval pass, so it is not free — use it to place
    chunk boundaries, not in hot paths.
    """
    url = (url or os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")).rstrip("/")
    req = {
        "model": model,
        "stream": False,
        "think": False,
        "keep_alive": "5m",
        "messages": [{"role": "user", "content": text}],
        "options": {"num_predict": 1},
    }
    try:
        r = urllib.request.urlopen(
            urllib.request.Request(
                url + "/api/chat", data=json.dumps(req).encode(),
                headers={"Content-Type": "application/json"},
            ),
            timeout=900,
        )
        return int(json.loads(r.read().decode()).get("prompt_eval_count", -1))
    except Exception:
        return -1


def chunk_text_exact(text, model, target_tokens, overlap_tokens, chars_per_token):
    """Chunk so each piece is ≤ target_tokens, verified by the real tokenizer.

    Uses tokenize() to shrink any chunk that exceeds the budget; falls back to the
    char estimate when the tokenizer is unavailable. Overlap is char-estimated
    (it is a safety margin, not a hard constraint).
    """
    chunks = []
    start = 0
    n = len(text)
    i = 0
    est_chars = max(1, int(target_tokens * chars_per_token))
    while start < n:
        end = min(start + est_chars, n)
        cnt = -1
        for _ in range(3):
            cnt = tokenize(text[start:end], model)
            if cnt < 0 or cnt <= target_tokens:
                break
            end = start + max(1, int((end - start) * target_tokens / cnt))
        chunks.append({
            "i": i, "start": start, "end": end,
            "text": text[start:end], "tokens": cnt if cnt > 0 else None,
        })
        if end >= n:
            break
        start = max(start + 1, end - int(overlap_tokens * chars_per_token))
        i += 1
    return chunks


def page_offset_map(pages):
    """[(page_num, char_start_offset), ...] for pages joined with a single newline."""
    offsets = []
    pos = 0
    for p in pages:
        offsets.append((p["page"], pos))
        pos += len(p["text"]) + 1  # +1 for the join newline
    return offsets


def char_to_page(offset, page_offsets):
    """1-based page number containing char `offset` (deterministic, no LLM)."""
    page = 1
    for pno, start in page_offsets:
        if offset >= start:
            page = pno
        else:
            break
    return page


def summarize_chunks(text, tokens, model, chunk_tokens, overlap_tokens, chars_per_token,
                     max_chunks=0, exact=True, page_offsets=None):
    """Map-reduce: chunk (exact token boundaries), LLM-tag each, concatenate.

    Returns (merged_summary, chunk_records). When page_offsets is given, each record
    carries a deterministic page_start/page_end and the merged doc is a page map
    ("CHUNK n (pages a–b)") — the LLM only supplies the rough topic list.
    """
    chunks = (
        chunk_text_exact(text, model, chunk_tokens, overlap_tokens, chars_per_token)
        if exact else
        chunk_text(text, int(chunk_tokens * chars_per_token), int(overlap_tokens * chars_per_token))
    )
    records = []
    for c in chunks:
        if max_chunks and len(records) >= max_chunks:
            break
        s = llm_brief(c["text"], tokens, CHUNK_SYSPROMPT.format(tokens=tokens))
        if s:
            rec = {"i": c["i"], "start": c["start"], "end": c["end"], "summary": s}
            if page_offsets is not None:
                rec["page_start"] = char_to_page(c["start"], page_offsets)
                rec["page_end"] = char_to_page(max(c["start"], c["end"] - 1), page_offsets)
            records.append(rec)
    def header(r):
        if "page_start" in r:
            return f"## CHUNK {r['i'] + 1} (pages {r['page_start']}–{r['page_end']})"
        return f"## CHUNK {r['i'] + 1} (chars {r['start']}–{r['end']})"
    merged = "\n\n".join(header(r) + "\n" + r["summary"] for r in records)
    return merged, records


# -------------------------------------------------------------------- build --
def build_card(root, relpath, abspath, opts):
    data = read_bytes(abspath)
    fp = fingerprint(data)
    size = len(data)
    mtime = os.path.getmtime(abspath)
    card = {
        "path": relpath.replace(os.sep, "/"),
        "fingerprint": fp,
        "size": size,
        "mtime": mtime,
        "builtAt": time.time(),
    }
    is_pdf = os.path.splitext(relpath)[1].lower() == PDF_EXT
    pages = []
    if is_pdf:
        pages = pdf_pages(abspath, opts.anchor_chars)
        anchors, page_index, n_pages = extract_pdf_anchors(pages, 400)
        card["kind"] = "pdf"
        card["pages"] = n_pages
        card["anchors"] = anchors
        card["pageIndex"] = page_index
    else:
        text = data[: opts.anchor_chars].decode("utf-8", "replace")
        card["kind"] = "text"
        card["anchors"] = extract_anchors(text, 400)
    if opts.summarize and size >= opts.summarize_min:
        if is_pdf:
            # Structure-agnostic map-reduce: cut the full text into context-sized
            # chunks with overlap, LLM-tag each, concatenate into a page map.
            pages = pdf_pages(abspath, 0)
            full_text = "\n".join(p["text"] for p in pages)
            page_offsets = page_offset_map(pages)
            model = os.environ.get("DIGEST_MODEL", "qwen3.5:2b-mlx")
            merged, chunks = summarize_chunks(
                full_text, opts.summary_tokens, model, opts.chunk_tokens,
                opts.overlap_tokens, opts.chars_per_token, opts.max_chunks,
                exact=not opts.estimate_chunks, page_offsets=page_offsets,
            )
            if merged:
                card["summary"] = merged
                card["chunks"] = chunks
                card["summaryModel"] = os.environ.get("DIGEST_MODEL", "qwen3.5:2b-mlx")
        else:
            s = summarize(abspath, opts.anchor_chars, opts.summary_tokens)
            if s:
                card["summary"] = s
                card["summaryModel"] = os.environ.get("DIGEST_MODEL", "qwen3.5:2b-mlx")
    return card, fp


def build(root, outdir, opts):
    root = os.path.abspath(root)
    outdir = os.path.abspath(outdir)
    cards_dir = os.path.join(outdir, "cards")
    os.makedirs(cards_dir, exist_ok=True)
    manifest_path = os.path.join(outdir, "index.json")

    old = {}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as fh:
                old = json.load(fh).get("files", {})
        except Exception:
            old = {}

    files = {}
    n_anchors = n_summaries = n_reused = 0
    for relpath, abspath in iter_files(root, outdir, opts.max_files, opts.max_bytes):
        data = read_bytes(abspath)
        fp = fingerprint(data)
        size = len(data)
        wants_summary = opts.summarize and size >= opts.summarize_min
        card_name = sha256_hex(relpath.replace(os.sep, "/").encode("utf-8"))[:24] + ".json"
        existing = old.get(relpath)
        if (
            not opts.force
            and existing is not None
            and existing.get("fingerprint") == fp
            and (not wants_summary or existing.get("summary"))
        ):
            # Reuse the persisted card as-is (anchors/summary are content-derived),
            # but never reuse a summary-less card when a summary is now requested.
            with open(os.path.join(cards_dir, card_name), "r", encoding="utf-8") as fh:
                card = json.load(fh)
            changed = False
        else:
            card, fp = build_card(root, relpath, abspath, opts)
            changed = True
            with open(os.path.join(cards_dir, card_name), "w", encoding="utf-8") as fh:
                json.dump(card, fh, ensure_ascii=False, indent=2)
        has_summary = bool(card.get("summary") or card.get("chunks"))
        files[relpath] = {
            "fingerprint": fp,
            "card": "cards/" + card_name,
            "size": card["size"],
            "mtime": card["mtime"],
            "kind": card["kind"],
            "pages": card.get("pages"),
            "anchors": len(card.get("anchors", [])),
            "chunks": len(card.get("chunks", [])),
            "summary": has_summary,
        }
        n_anchors += len(card.get("anchors", []))
        n_summaries += 1 if has_summary else 0
        n_reused += 0 if changed else 1

    # Drop cards whose file vanished or changed beyond manifest (orphan cleanup).
    for relpath in list(old):
        if relpath not in files:
            old_entry = old[relpath]
            card_rel = old_entry.get("card", "")
            orphan = os.path.join(outdir, card_rel) if card_rel else ""
            if orphan and os.path.exists(orphan):
                os.remove(orphan)

    manifest = {
        "version": 1,
        "root": root,
        "builtAt": time.time(),
        "policy": {
            "maxFiles": opts.max_files,
            "maxBytes": opts.max_bytes,
            "anchorChars": opts.anchor_chars,
            "summarizeMinBytes": opts.summarize_min,
            "summaryTokens": opts.summary_tokens,
        },
        "files": files,
    }
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    print(
        f"index: {len(files)} files · {n_anchors} anchors · "
        f"{n_summaries} summaries · {n_reused} reused · -> {outdir}",
        file=sys.stderr,
    )
    return 0


# ------------------------------------------------------------------ lookup --
def load_manifest(outdir):
    with open(os.path.join(outdir, "index.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


def lookup(root, outdir, path, as_json):
    root = os.path.abspath(root)
    outdir = os.path.abspath(outdir)
    if not os.path.exists(os.path.join(outdir, "index.json")):
        print("digest-index: no index yet — run `./digest_index.sh build`", file=sys.stderr)
        return 2
    rel = os.path.relpath(os.path.abspath(path), root)
    rel = rel.replace(os.sep, "/")
    if rel.startswith("../"):
        print(f"digest-index: {path} is outside root {root}", file=sys.stderr)
        return 2
    man = load_manifest(outdir)
    entry = man.get("files", {}).get(rel)
    if entry is None:
        print(f"digest-index: MISS (not indexed): {rel}")
        return 1
    if not os.path.exists(path):
        print(f"digest-index: STALE (file gone): {rel}")
        return 1
    cur_fp = fingerprint(read_bytes(path))
    if cur_fp != entry["fingerprint"]:
        print(f"digest-index: STALE (content changed, hash {cur_fp[:18]}… != {entry['fingerprint'][:18]}…): {rel}")
        return 1
    card_path = os.path.join(outdir, entry["card"])
    with open(card_path, "r", encoding="utf-8") as fh:
        card = json.load(fh)
    if as_json:
        json.dump(card, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    print(f"digest-index: FRESH {rel}")
    pages = card.get("pages")
    n_chunks = len(card.get("chunks", []))
    print(f"  kind={card.get('kind')} size={card.get('size')} "
          f"pages={pages if pages is not None else '-'} "
          f"anchors={len(card.get('anchors', []))} "
          f"chunks={n_chunks} summary={'yes' if card.get('summary') else 'no'}")
    for c in card.get("chunks", [])[:40]:
        print(f"  [chunk {c.get('i', 0) + 1} · chars {c.get('start')}-{c.get('end')}]")
        for line in c.get("summary", "").splitlines()[:8]:
            print(f"      {line}")
    page_index = card.get("pageIndex", [])[:40]
    if page_index:
        print(f"  page index (first {len(page_index)}):")
        for pi in page_index:
            print(f"    p{pi['page']:>3}  {pi['label'][:90]}")
    anchors = card.get("anchors", [])[:40]
    if anchors:
        print(f"  anchors (first {len(anchors)}):")
        for a in anchors:
            page = f" p{a['page']:<3}" if "page" in a else "     "
            print(f"    [{a['type']:8}]{page} {a['text']}")
    return 0


# ------------------------------------------------------------------ status --
def status(root, outdir):
    outdir = os.path.abspath(outdir)
    mp = os.path.join(outdir, "index.json")
    if not os.path.exists(mp):
        print("no index")
        return 1
    man = load_manifest(outdir)
    files = man.get("files", {})
    n_sum = sum(1 for f in files.values() if f.get("summary"))
    n_anc = sum(f.get("anchors", 0) for f in files.values())
    print(f"root={man.get('root')} builtAt={man.get('builtAt', 0):.0f}")
    print(f"files={len(files)} summaries={n_sum} anchors={n_anc}")
    return 0


# ------------------------------------------------------------------- slice --
def _parse_range(spec):
    """'A-B' -> (A, B); 'A' -> (A, A). Raises ValueError on bad input."""
    spec = spec.strip()
    if "-" in spec:
        a, b = spec.split("-", 1)
        return int(a), int(b)
    return int(spec), int(spec)


def slice_cmd(path, pages, chars, maxchars=0):
    """Extract a page range (--pages A-B) or char range (--chars X-Y) of a PDF."""
    if pages:
        a, b = _parse_range(pages)
        text = pdf_slice(path, a, b, maxchars)
        if not text:
            print(f"digest-index: no text for pages {a}-{b}", file=sys.stderr)
            return 1
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        return 0
    if chars:
        x, y = _parse_range(chars)
        full = "\n".join(p["text"] for p in pdf_pages(path, 0))
        sys.stdout.write(full[x:y])
        return 0
    print("digest-index: give --pages A-B or --chars X-Y", file=sys.stderr)
    return 2


# -------------------------------------------------------------------- main --
def parse():
    p = argparse.ArgumentParser(description="Eager workspace digest index")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build/refresh the index")
    b.add_argument("root", nargs="?", default=".")
    b.add_argument("--out", default=".dsh/digest")
    b.add_argument("--summarize", action="store_true", help="LLM-summarize big files")
    b.add_argument("--force", action="store_true", help="rebuild cards even if unchanged")
    b.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    b.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    b.add_argument("--anchor-chars", type=int, default=DEFAULT_ANCHOR_CHARS)
    b.add_argument("--summarize-min", type=int, default=DEFAULT_SUMMARIZE_MIN_BYTES)
    b.add_argument("--summary-tokens", type=int, default=DEFAULT_SUMMARY_TOKENS,
                   help="per-chunk brief length")
    b.add_argument("--chunk-tokens", type=int, default=DEFAULT_CHUNK_TOKENS,
                   help="target chunk size in tokens (fits the context window)")
    b.add_argument("--overlap-tokens", type=int, default=DEFAULT_OVERLAP_TOKENS,
                   help="tail overlap between chunks in tokens")
    b.add_argument("--chars-per-token", type=float, default=DEFAULT_CHARS_PER_TOKEN,
                   help="conservative chars/token estimate for chunking")
    b.add_argument("--max-chunks", type=int, default=0,
                   help="cap on chunks to summarize (0 = all); useful for testing")
    b.add_argument("--estimate-chunks", action="store_true",
                   help="skip the tokenizer and cut by char estimate (faster, less exact)")
    b.add_argument("--fine", action="store_true",
                   help="fine routing preset: ~12k-token chunks (~15 pages) instead of ~60k")

    l = sub.add_parser("lookup", help="look up one file's card (fresh/stale/miss)")
    l.add_argument("root", nargs="?", default=".")
    l.add_argument("path")
    l.add_argument("--out", default=".dsh/digest")
    l.add_argument("--json", action="store_true")

    s = sub.add_parser("status", help="show index summary")
    s.add_argument("root", nargs="?", default=".")
    s.add_argument("--out", default=".dsh/digest")

    c = sub.add_parser("clean", help="delete the index")
    c.add_argument("--out", default=".dsh/digest")

    sl = sub.add_parser("slice", help="extract a page/char slice of a PDF")
    sl.add_argument("path")
    sl.add_argument("--pages", help="page range A-B (1-based, inclusive)")
    sl.add_argument("--chars", help="char range X-Y in the extracted text")
    return p


def main(argv=None):
    p = parse()
    args = p.parse_args(argv)
    if getattr(args, "cmd", None) == "build" and getattr(args, "fine", False):
        args.chunk_tokens = 12000
        args.overlap_tokens = 1000
    if args.cmd == "build":
        return build(args.root, args.out, args)
    if args.cmd == "lookup":
        return lookup(args.root, args.out, args.path, args.json)
    if args.cmd == "status":
        return status(args.root, args.out)
    if args.cmd == "slice":
        return slice_cmd(args.path, args.pages, args.chars)
    if args.cmd == "clean":
        import shutil
        outdir = os.path.abspath(args.out)
        if os.path.isdir(outdir):
            shutil.rmtree(outdir)
        print(f"cleaned {outdir}")
        return 0
    p.error("unknown command")
    return 2


if __name__ == "__main__":
    sys.exit(main())
