# digest_index — eager workspace digest index (prototype)

Pay the expensive prefill **once, in the background, at workspace init**, and
store the *result* as small per-file "cards" under `.dsh/digest/`. The real
model then looks up a file's card instead of pre-filling the raw bytes — no
60-second wait on the critical path.

## Quick start

```bash
./digest_index.sh build [ROOT] [--summarize] [--force]   # build/refresh index
./digest_index.sh lookup [ROOT] PATH                     # fresh / stale / miss
./digest_index.sh slice FILE --pages A-B                 # extract just pages A–B
./digest_index.sh status [ROOT]                          # index summary
./digest_index.sh clean                                  # delete index
./digest_index.sh start [ROOT] [--summarize]             # build in background (init hook)
```

`ROOT` defaults to `.`; the index lands in `.dsh/digest/` (`DIGEST_INDEX_DIR`
overrides). `start` is the "runs when a workspace is initialized" wiring — call
it from a session/workspace init hook (later: a DSH plugin hooking `agent/pre-step`).

## Layout

```
.dsh/digest/
├── index.json                 manifest: root, policy, per-file {fingerprint, card, …}
├── cards/<sha256path>.json     one card per file (path-hashed → overwritten in place)
└── run.log / run.pid           written by `start`
```

## The three tiers (one index)

1. **Structural anchors — no LLM, deterministic, always built.** Section headers,
   `#define`/assignment identifiers, hex addresses (`0x0020`), value+unit tokens
   (`0,1 ml`). These are cheap *pointers* into the raw file. **For PDFs the
   extractor is page-aware** (`pdf_pages.py`): every anchor carries its page and
   the card includes a `pageIndex`, so the reader can extract just the one page
   a fact lives on instead of the whole document.
2. **Map-reduce LLM summary — optional, structure-agnostic** for files ≥
   `--summarize-min` (40 KB). The full extracted text is cut into **context-sized
   chunks with overlap** (`--chunk-tokens`, default 60000; `--overlap-tokens`,
   default 2000; `--chars-per-token`, default 3.0), each chunk is summarized by
   the local model, and all chunk summaries are **concatenated into one document**
   (`card.summary` + `card.chunks`). No reliance on headings/sections — it works
   on any PDF or long text.
3. **Focused digest — not here.** Still `digest.sh`, but now the material is
   cached by `prewarm.py` and the index tells you *where* to look.

Read path for the real model: look up card → anchors/summary answer it? done →
else read just the pointed-to slice → else focused digest.

## Invalidation (the part that must not be wrong)

Every card is keyed by the file's **content hash** (`sha256`). `lookup` re-hashes
the file and refuses a card whose hash no longer matches:

```
$ ./digest_index.sh lookup task_aquarack_v3 docs/pumpdriver-manual.pdf
digest-index: FRESH docs/pumpdriver-manual.pdf
$ # edit the file…
$ ./digest_index.sh lookup task_aquarack_v3 docs/pumpdriver-manual.pdf
digest-index: STALE (content changed, hash …): docs/pumpdriver-manual.pdf   # exit 1
```

A stale summary is worse than none — it is never returned.

## Env

- `DIGEST_INDEX_DIR` — output dir (default `.dsh/digest`)
- `OLLAMA_URL` — base URL for summaries (default `http://127.0.0.1:11434`)
- `DIGEST_MODEL` / `DIGEST_TIMEOUT` / `DIGEST_NUM_CTX` / `DIGEST_KEEP_ALIVE` — pass through

Note: summaries need the model loaded. The bundled Ollama + models live under
`.pilot/` — start it with `OLLAMA_MODELS="$PWD/.pilot/models" .pilot/ollama/ollama serve`
(pick a free port and set `OLLAMA_URL` to match).
