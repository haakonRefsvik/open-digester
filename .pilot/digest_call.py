import os, sys, json, urllib.request, socket

model = os.environ["MODEL"]
tokens = int(os.environ["TOKENS"])
focus = os.environ["FOCUS"].strip()
url = os.environ["OLLAMA_URL"].rstrip("/")
material = sys.stdin.read()
think_on = os.environ.get("THINK", "0") == "1"
timeout = int(os.environ.get("TIMEOUT", "60"))
num_ctx = int(os.environ.get("NUM_CTX", "32768"))
keep_alive = os.environ.get("KEEP_ALIVE", "30m")
num_predict = int(os.environ.get("NUM_PREDICT", "0")) or max(4096, tokens * 16)

sysprompt = os.environ.get("DIGEST_SYSPROMPT") or (
    f"You are a precise local extraction assistant. Produce a tight brief of at most {tokens} tokens "
    "from the provided material. Rules: quote exact identifiers, file paths, function names and "
    "signatures verbatim and ONLY as they appear in the material; NEVER invent content, paths or APIs "
    "not present; if something is not present in the material, say NOT_FOUND. Group your output by "
    "FILE/STDIN. No preamble, no meta commentary."
)

# Material FIRST (stable prefix the KV cache can reuse), focus question LAST
# (short variable tail). Keeps the expensive part byte-identical across queries.
messages = [
    {"role": "system", "content": sysprompt},
    {"role": "user", "content": "MATERIAL:\n" + material},
]
if focus:
    messages.append(
        {"role": "user", "content": "FOCUS QUESTION (answer from the material only): " + focus}
    )

req = {
    "model": model,
    "think": think_on,
    "stream": False,
    "keep_alive": keep_alive,
    "messages": messages,
    "options": {
        "num_predict": num_predict,
        "num_ctx": num_ctx,
    },
}

data = json.dumps(req).encode()
try:
    r = urllib.request.urlopen(
        urllib.request.Request(url + "/api/chat", data=data,
                               headers={"Content-Type": "application/json"}),
        timeout=timeout,
    )
except socket.timeout:
    print(
        f"digest: TIMEOUT after {timeout}s — the local model is too slow; "
        "read the file directly with your own tools instead",
        file=sys.stderr,
    )
    sys.exit(124)
except Exception as e:
    print(f"digest: failed to reach {url}: {e}", file=sys.stderr)
    sys.exit(1)

resp = json.loads(r.read().decode())
if "error" in resp:
    print(f"digest: server error: {resp['error']}", file=sys.stderr)
    sys.exit(1)

if os.environ.get("DIGEST_TIMINGS") == "1":
    t = resp.get("timings", {}) or {}
    pe = resp.get("prompt_eval_count", t.get("prompt_eval_count"))
    pd_s = (resp.get("prompt_eval_duration", t.get("prompt_eval_duration", 0)) or 0) / 1e9
    ec = resp.get("eval_count", t.get("eval_count"))
    ed_s = (resp.get("eval_duration", t.get("eval_duration", 0)) or 0) / 1e9
    td_s = (resp.get("total_duration", t.get("total_duration", 0)) or 0) / 1e9
    print(
        f"[timing] prompt_eval_count={pe} prompt_eval_s={pd_s:.2f} "
        f"eval_count={ec} eval_s={ed_s:.2f} total_s={td_s:.2f}",
        file=sys.stderr,
    )

content = (resp["message"].get("content") or "").strip()
if not content:
    print("digest: model returned empty content", file=sys.stderr)
    sys.exit(1)
print(content)
