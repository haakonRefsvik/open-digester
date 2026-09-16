#!/usr/bin/env bash
# digest_prewarm — load the model and pre-fill its KV cache for the given files,
# so later `digest.sh` queries on the same files are warm (cache hit).
#
# Run this in the BACKGROUND at session start:
#   ./digest_prewarm.sh docs/manual.pdf logs/serial.log &
#
# It builds the canonical material once (stored under .pilot/tmp/prewarm/),
# seeds the model (system + MATERIAL, no question), and writes a .ready marker.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
MODEL="${DIGEST_MODEL:-qwen3.5:4b-mlx}"
TOKENS="${DIGEST_TOKENS:-400}"
NUM_CTX="${DIGEST_NUM_CTX:-65536}"
KEEP_ALIVE="${DIGEST_KEEP_ALIVE:-30m}"
SEED_TIMEOUT="${DIGEST_SEED_TIMEOUT:-900}"
PER_FILE_CHARS="${DIGEST_CHARS:-20000}"
THINK=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -c|--chars)  PER_FILE_CHARS="$2"; shift 2;;
    -m|--model)  MODEL="$2"; shift 2;;
    -t|--tokens) TOKENS="$2"; shift 2;;
    -n|--ctx)    NUM_CTX="$2"; shift 2;;
    -w|--timeout) SEED_TIMEOUT="$2"; shift 2;;
    -T|--think)  THINK=1; shift;;
    --) shift; break;;
    -*) echo "unknown option: $1" >&2; exit 2;;
    *) break;;
  esac
done

[[ $# -gt 0 ]] || { echo "usage: digest_prewarm.sh [opts] FILE..." >&2; exit 2; }

status=0
for f in "$@"; do
  [[ -f "$f" ]] || { echo "warn: skip missing $f" >&2; continue; }
  if ! python3 "$ROOT/.pilot/prewarm.py" seed "$f" "$PER_FILE_CHARS" "$MODEL" "$TOKENS" \
        "$NUM_CTX" "$THINK" "$KEEP_ALIVE" "$SEED_TIMEOUT" "$OLLAMA_URL"; then
    echo "warn: prewarm failed for $f (see .ready)" >&2
    status=1
  fi
done
exit "$status"
