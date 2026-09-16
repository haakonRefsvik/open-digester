#!/usr/bin/env python3
"""Benchmark local models on a fixed chunk-summarization task.

Usage:
    bench_models.py CHUNK_FILE [tokens] [model ...]

Calls /api/chat directly (same chunk-summary prompt as the index), records exact
prompt_eval_count / durations, saves each summary, and prints a JSON report.

Env: OLLAMA_URL (default http://127.0.0.1:11434)
"""
import json
import os
import sys
import time
import urllib.request

CHUNK_PROMPT = (
    "You are summarizing ONE contiguous chunk of a larger document for a retrieval index. "
    "Produce a dense, faithful summary of this chunk in at most {tokens} tokens. Preserve: "
    "key entities, definitions, variables, equations with their numbers, algorithms, and "
    "findings. Quote exact identifiers and equation references verbatim. Do NOT invent "
    "anything not in the chunk. If the chunk starts or ends mid-sentence, ignore the "
    "fragment. No preamble, no meta commentary."
)


def chat(model, material, tokens, url):
    req = {
        "model": model,
        "stream": False,
        "keep_alive": "5m",
        "think": False,
        "messages": [
            {"role": "system", "content": CHUNK_PROMPT.format(tokens=tokens)},
            {"role": "user", "content": "MATERIAL:\n" + material},
        ],
        "options": {"num_predict": max(4096, tokens * 16), "num_ctx": 65536},
    }
    t0 = time.time()
    r = urllib.request.urlopen(
        urllib.request.Request(
            url + "/api/chat", data=json.dumps(req).encode(),
            headers={"Content-Type": "application/json"},
        ),
        timeout=900,
    )
    d = json.loads(r.read().decode())
    return d, time.time() - t0


def main():
    f = sys.argv[1]
    tokens = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    models = sys.argv[3:] or ["qwen3.5:2b-mlx", "qwen3.5:4b-mlx", "gemma4:12b-mlx"]
    url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    material = open(f, encoding="utf-8", errors="replace").read()

    results = []
    for m in models:
        d, wall = chat(m, material, tokens, url)
        pe = d.get("prompt_eval_count", 0)
        pe_s = (d.get("prompt_eval_duration", 0) or 0) / 1e9
        ec = d.get("eval_count", 0)
        ev_s = (d.get("eval_duration", 0) or 0) / 1e9
        td_s = (d.get("total_duration", 0) or 0) / 1e9
        summary = (d.get("message", {}).get("content") or "").strip()
        out = {
            "model": m,
            "input_tokens": pe,
            "prefill_s": round(pe_s, 2),
            "prefill_tok_s": round(pe / pe_s, 1) if pe_s else None,
            "output_tokens": ec,
            "eval_s": round(ev_s, 2),
            "eval_tok_s": round(ec / ev_s, 1) if ev_s else None,
            "total_s": round(td_s, 2),
            "wall_s": round(wall, 2),
        }
        results.append(out)
        fn = "/tmp/bench_" + m.replace(":", "_").replace("/", "_") + ".md"
        with open(fn, "w", encoding="utf-8") as fh:
            fh.write(summary)
        print(f"[{m}] done in {wall:.0f}s — summary -> {fn}", file=sys.stderr)

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
