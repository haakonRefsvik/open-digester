#!/usr/bin/env python3
"""Prewarm the Ollama KV cache for digest.sh.

The prefix cache only reuses an EXACT byte-identical prompt prefix. So we build
the canonical material for a file once, store it, and send one "seed" request
(system + MATERIAL, no focus question). A later digest query sends the same
prefix plus a short focus-question tail, so the expensive prefill is a cache hit.

Subcommands:
  key      <path> <cap> <model> <tokens> <num_ctx> <think>     -> cache key (sha256)
  material <path> <cap>                                        -> canonical material text
  seed     <path> <cap> <model> <tokens> <num_ctx> <think> <keep_alive> <timeout> [url]
      build+store material, seed the model, write .ready marker
"""
import os, sys, hashlib, json, subprocess, time

PILOT = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(PILOT, "tmp", "prewarm")


def run(args):
    return subprocess.run(args, capture_output=True, text=True)


def build_material(path, cap):
    """Mirror digest.sh's file loop byte-for-byte (single file)."""
    if not os.path.isfile(path):
        return ""
    is_pdf = path.lower().endswith(".pdf")
    if not is_pdf:
        r = run(["file", "-b", path])
        if r.returncode == 0 and "pdf document" in r.stdout.lower():
            is_pdf = True
    if is_pdf:
        size = os.path.getsize(path)
        r = run([sys.executable, os.path.join(PILOT, "pdf_extract.py"), path, str(cap)])
        if r.returncode == 0:
            return f"\n### FILE: {path} ({size} bytes, PDF)\n{r.stdout}"
        return ""
    r = run(["file", "-b", path])
    if r.returncode == 0 and any(
        k in r.stdout.lower() for k in ("executable", "binary", "image", "archive", "compressed")
    ):
        return ""
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        raw = fh.read(cap)
    data = raw.decode("utf-8", "replace")
    body = f"\n### FILE: {path} ({size} bytes)\n{data}"
    if size > cap:
        body += f"\n...[truncated at {cap} chars]"
    return body


def cache_key(path, cap, model, tokens, num_ctx, think):
    s = "\x1f".join([os.path.abspath(path), str(cap), model, str(tokens), str(num_ctx), str(think)])
    return hashlib.sha256(s.encode()).hexdigest()


def seed(path, cap, model, tokens, num_ctx, think, keep_alive, timeout, url):
    key = cache_key(path, cap, model, tokens, num_ctx, think)
    material = build_material(path, cap)
    os.makedirs(CACHE_DIR, exist_ok=True)
    mat_path = os.path.join(CACHE_DIR, key + ".material")
    with open(mat_path, "w", encoding="utf-8") as fh:
        fh.write(material)

    env = dict(os.environ)
    env.update({
        "MODEL": model,
        "TOKENS": str(tokens),
        "FOCUS": "",
        "THINK": str(think),
        "TIMEOUT": str(timeout),
        "NUM_CTX": str(num_ctx),
        "KEEP_ALIVE": keep_alive,
        "NUM_PREDICT": "1",
        "OLLAMA_URL": url,
    })
    t0 = time.time()
    p = subprocess.run(
        [sys.executable, os.path.join(PILOT, "digest_call.py")],
        input=material, capture_output=True, text=True, env=env,
    )
    elapsed = time.time() - t0
    ready = {
        "key": key, "path": os.path.abspath(path), "cap": cap, "model": model,
        "tokens": tokens, "num_ctx": num_ctx, "think": think,
        "material_bytes": len(material.encode("utf-8")),
        "seed_ok": p.returncode == 0,
        "seed_elapsed_s": round(elapsed, 2),
        "ts": time.time(),
    }
    if p.returncode == 0:
        with open(os.path.join(CACHE_DIR, key + ".brief"), "w", encoding="utf-8") as fh:
            fh.write(p.stdout)
    else:
        ready["seed_error"] = (p.stderr or "").strip()[-500:]
    with open(os.path.join(CACHE_DIR, key + ".ready"), "w", encoding="utf-8") as fh:
        json.dump(ready, fh, indent=2)
    print(f"prewarm: {path} -> key {key[:12]}… seed_ok={p.returncode == 0} {elapsed:.1f}s", file=sys.stderr)
    return 0 if p.returncode == 0 else 1


def main():
    argv = sys.argv[1:]
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    cmd = argv[0]
    if cmd == "key":
        path, cap, model, tokens, num_ctx, think = argv[1:7]
        print(cache_key(path, int(cap), model, int(tokens), int(num_ctx), int(think)))
    elif cmd == "material":
        path, cap = argv[1], int(argv[2])
        sys.stdout.write(build_material(path, cap))
    elif cmd == "seed":
        path, cap, model, tokens, num_ctx, think, keep_alive, timeout = argv[1:9]
        url = argv[9] if len(argv) > 9 else "http://127.0.0.1:11434"
        return seed(path, int(cap), model, int(tokens), int(num_ctx), int(think),
                    keep_alive, int(timeout), url)
    else:
        print(f"unknown subcommand: {cmd}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
