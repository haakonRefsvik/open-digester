#!/usr/bin/env bash
# digest_index — eager workspace digest index (build once in background, look up fast).
#
# Usage:
#   ./digest_index.sh build [ROOT] [--summarize] [--force]   build/refresh the index
#   ./digest_index.sh lookup [ROOT] PATH                     look up one file's card
#   ./digest_index.sh status [ROOT]                          show index summary
#   ./digest_index.sh slice FILE --pages A-B                 extract just pages A-B
#   ./digest_index.sh clean [ROOT]                           delete the index
#   ./digest_index.sh start [ROOT] [--summarize]             build in the BACKGROUND (init hook)
#
# The index lands in .dsh/digest/ by default. Env:
#   DIGEST_INDEX_DIR  override output dir (default .dsh/digest)
#   DIGEST_MODEL / DIGEST_TIMEOUT / DIGEST_NUM_CTX / OLLAMA_URL  pass through to summaries

set -eo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$ROOT_DIR/.pilot/index_build.py"
OUT="${DIGEST_INDEX_DIR:-.dsh/digest}"

usage() { sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; }

cmd="${1:-}"
shift || true

case "$cmd" in
  build)
    # Split: a leading non-flag arg is ROOT; everything else passes through.
    root="."
    rest=()
    for a in "$@"; do
      if [[ "$a" != -* && "$root" == "." ]]; then root="$a"; else rest+=("$a"); fi
    done
    python3 "$PY" build "$root" --out "$OUT" "${rest[@]}"
    ;;
  lookup)
    pos=()
    json=""
    for a in "$@"; do
      case "$a" in
        --json) json="--json";;
        -*) echo "unknown option: $a" >&2; exit 2;;
        *) pos+=("$a");;
      esac
    done
    if [[ ${#pos[@]} -eq 1 ]]; then root="."; path="${pos[0]}"; \
    elif [[ ${#pos[@]} -eq 2 ]]; then root="${pos[0]}"; path="${pos[1]}"; \
    else usage >&2; exit 2; fi
    python3 "$PY" lookup "$root" "$path" --out "$OUT" $json
    ;;
  status)
    python3 "$PY" status "${1:-.}" --out "$OUT"
    ;;
  slice)
    path=""
    pages=""
    chars=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --pages) pages="${2:-}"; shift 2;;
        --chars) chars="${2:-}"; shift 2;;
        -*) echo "unknown option: $1" >&2; exit 2;;
        *) path="$1"; shift;;
      esac
    done
    [[ -n "$path" ]] || { usage >&2; exit 2; }
    args=("$path")
    [[ -n "$pages" ]] && args+=(--pages "$pages")
    [[ -n "$chars" ]] && args+=(--chars "$chars")
    python3 "$PY" slice "${args[@]}"
    ;;
  clean)
    python3 "$PY" clean --out "$OUT"
    ;;
  start)
    root="${1:-.}"
    summarize=""
    [[ "${2:-}" == "--summarize" ]] && summarize="--summarize"
    mkdir -p "$OUT"
    log="$OUT/run.log"
    nohup python3 "$PY" build "$root" --out "$OUT" $summarize >"$log" 2>&1 &
    echo $! > "$OUT/run.pid"
    echo "started background build: pid $(cat "$OUT/run.pid") (log: $log)"
    ;;
  -h|--help|"")
    usage
    [[ -z "$cmd" ]] && exit 2
    exit 0
    ;;
  *)
    echo "unknown command: $cmd" >&2
    usage >&2
    exit 2
    ;;
esac
