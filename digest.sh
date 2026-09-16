#!/usr/bin/env bash
# digest — compress files or stdin into a tight brief via a local Ollama model.
#
# Usage:
#   digest.sh [opts] FILE...      digest files (read locally; cloud context never sees raw content)
#   digest.sh [opts] -            digest stdin (e.g.  long_cmd | digest.sh -)
#
# Options:
#   -t/--tokens N   target brief length in tokens (default 400)
#   -m/--model M    model id (default qwen3.5:4b-mlx)
#   -c/--chars N    per-file input cap in chars (default 20000)
#   -q/--query S    focus question to answer from the material
#   -w/--timeout N  max seconds for the local call before falling back (default 60)
#   -n/--ctx N      context window in tokens (default 65536; needs room for big files)
#   -T/--think      enable model thinking (default off; off is faster)
#   PDF files are auto-extracted to text first (pdftotext, or bundled pypdf).
#
# Env:
#   OLLAMA_URL        server base URL (default http://127.0.0.1:11434)
#   DIGEST_MODEL      override default model
#   DIGEST_TIMEOUT    override default timeout (seconds)
#   DIGEST_NUM_CTX    override context window (tokens)
#   DIGEST_KEEP_ALIVE override model keep-alive (default 30m)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
MODEL="${DIGEST_MODEL:-qwen3.5:4b-mlx}"
TOKENS=400
TIMEOUT="${DIGEST_TIMEOUT:-60}"
NUM_CTX="${DIGEST_NUM_CTX:-65536}"
KEEP_ALIVE="${DIGEST_KEEP_ALIVE:-30m}"
PER_FILE_CHARS=20000
TOTAL_CHARS=120000
FOCUS=""
THINK=0

usage() { sed -n '2,23p' "$0" | sed 's/^# \{0,1\}//'; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--tokens) TOKENS="$2"; shift 2;;
    -m|--model)  MODEL="$2"; shift 2;;
    -c|--chars)  PER_FILE_CHARS="$2"; shift 2;;
    -q|--query)  FOCUS="$2"; shift 2;;
    -w|--timeout) TIMEOUT="$2"; shift 2;;
    -n|--ctx)     NUM_CTX="$2"; shift 2;;
    -T|--think)  THINK=1; shift;;
    -h|--help)   usage; exit 0;;
    --) shift; break;;
    -*) echo "unknown option: $1" >&2; exit 2;;
    *) break;;
  esac
done

if [[ $# -eq 0 && -t 0 ]]; then usage >&2; exit 2; fi

# ---- Prewarm cache lookup (single file: reuse byte-identical material) ----
body=""
if [[ $# -eq 1 && -f "$1" ]]; then
  _key="$(python3 "$ROOT/.pilot/prewarm.py" key "$1" "$PER_FILE_CHARS" "$MODEL" "$TOKENS" "$NUM_CTX" "$THINK" 2>/dev/null || true)"
  _cmat="$ROOT/.pilot/tmp/prewarm/$_key.material"
  if [[ -n "$_key" && -f "$_cmat" ]]; then
    body="$(cat "$_cmat")"
  fi
fi

# ---- Build the raw material locally (reads files/stdio; capped) ----
if [[ -z "$body" ]]; then
if [[ $# -eq 0 || "$1" == "-" ]]; then
  data="$(head -c "$PER_FILE_CHARS")" || true
  body+=$'\n'"### STDIN (piped command output)"$'\n'"$data"
else
  for f in "$@"; do
    [[ -f "$f" ]] || { echo "warn: skip missing $f" >&2; continue; }
    is_pdf=0
    if [[ "$f" == *.pdf ]]; then is_pdf=1; fi
    if command -v file >/dev/null 2>&1 && file -b "$f" | grep -qi 'pdf document'; then is_pdf=1; fi
    if [[ "$is_pdf" -eq 1 ]]; then
      size=$(wc -c < "$f" | tr -d ' ')
      if data="$(python3 "$ROOT/.pilot/pdf_extract.py" "$f" "$PER_FILE_CHARS")"; then
        body+=$'\n'"### FILE: $f (${size} bytes, PDF)"$'\n'"$data"
      else
        echo "warn: kunne ikke trekke ut tekst fra PDF $f (pip/brew-melding ovenfor)" >&2
        continue
      fi
      continue
    fi
    if command -v file >/dev/null 2>&1 && file -b "$f" | grep -qiE 'executable|binary|image|archive|compressed'; then
      echo "warn: skip binary $f" >&2; continue
    fi
    size=$(wc -c < "$f" | tr -d ' ')
    data="$(head -c "$PER_FILE_CHARS" "$f")" || true
    body+=$'\n'"### FILE: $f (${size} bytes)"$'\n'"$data"
    if [[ "$size" -gt "$PER_FILE_CHARS" ]]; then
      body+=$'\n'"...[truncated at ${PER_FILE_CHARS} chars]"
    fi
  done
fi
fi

if [[ -z "$(printf '%s' "$body" | tr -d '[:space:]')" ]]; then
  echo "error: no text material to digest" >&2
  exit 1
fi

# ---- Call the local model, print the brief ----
printf '%s' "$body" | MODEL="$MODEL" TOKENS="$TOKENS" FOCUS="$FOCUS" THINK="$THINK" TIMEOUT="$TIMEOUT" NUM_CTX="$NUM_CTX" KEEP_ALIVE="$KEEP_ALIVE" OLLAMA_URL="$OLLAMA_URL" python3 "$ROOT/.pilot/digest_call.py"
