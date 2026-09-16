# open-digester

**Lokal-først digest av store filer.** I stedet for å fylle kontekstvinduet med
rå bytes fra en 40-siders PDF eller en 90 KB seriell-logg, komprimerer
open-digester materialet til en kort, trofast brief — produsert av en **lokal**
modell via [Ollama](https://ollama.com). Rå innholdet forlater aldri maskinen.

Prosjektet har tre deler som bygger på hverandre:

| Del | Fil | Idé |
|---|---|---|
| **Digest** | `digest.sh` | Komprimer filer/stdin til en brief på N tokens, med et fokusspørsmål. |
| **Prewarm** | `digest_prewarm.sh` | Varm opp KV-cachen i bakgrunnen, så senere spørringer blir treff i stedet for full prefill. |
| **Indeks** | `digest_index.sh` | Bygg en eager digest-indeks for hele arbeidsrommet ved oppstart, og slå opp filer i stedet for å lese dem. |

I tillegg ligger et lite **eval-harness** (`task_aquarack*`) som måler om digest
faktisk sparer tokens uten å miste fidelitet.

---

## Hvorfor

Å lese en stor fil koster prefill-tokens — én gang per spørring, hver gang.
To observasjoner driver designet:

1. **Prefill er dyr, og den er stabil.** Ollama gjenbruker prefix-cachen kun når
   prompt-prefikset er *byte-identisk*. Legger man materialet **først** og det
   korte spørsmålet **sist**, blir den dyre delen identisk på tvers av
   spørringer — og kan betales én gang, i bakgrunnen, før modellen trenger den.
2. **En kort brief er ofte nok.** For spørsmål av typen «hvilken enhet har
   register 0x0020?» er et ~200-tokens svar fra en fokusert digest like presist
   som å lese hele databladet — til en brøkdel av kostnaden.

Den viktigste korrekthetsegenskapen: **en utdatert oppsummering er farligere enn
ingen.** Derfor er hvert indekskort låst til filens innholdshash (se
[Invalidering](#invalidering)).

---

## Struktur

```
open-digester/
├── digest.sh                 # digest én eller flere filer (eller stdin) -> kort brief
├── digest_prewarm.sh         # varm KV-cachen for filer i bakgrunnen
├── digest_index.sh           # CLI for den eager indeksen
├── DIGEST_INDEX.md           # designdokument for indeksen
├── .pilot/
│   ├── index_build.py        # bygg/slå opp/status/slice for .dsh/digest/
│   ├── digest_call.py        # selve Ollama-kallet (material først, spørsmål sist)
│   ├── prewarm.py            # kanonisk material + seed-request + .ready-markør
│   ├── pdf_extract.py        # PDF -> tekst (pdftotext, ellers pypdf)
│   ├── pdf_pages.py          # PDF -> tekst MED sidegrenser (ankere peker på side)
│   ├── bench_models.py       # benchmark lokale modeller på chunk-oppsummering
│   ├── gen_pdf_v3.py         # genererer det syntetiske databladet til v3-oppgaven
│   └── FASIT_aquarack*.md    # fasit med scoringsskjema (skjult for modellen)
├── task_aquarack/            # eval: 10x-dosering, rotårsak i koden
├── task_aquarack_v2/         # eval: samme, men lokal #undef-overstyring skjuler feilen
└── task_aquarack_v3/         # eval: rotårsaken finnes KUN i PDF-databladet (40 sider)
```

---

## Forutsetninger

- **Python 3** (kun standardbiblioteket for indeksen)
- **Ollama** med en modell — standard er `qwen3.5:4b-mlx` (overstyr med `DIGEST_MODEL`)
- **Valgfritt:** `pdftotext` (poppler) for PDF-uttrekk. Uten den brukes `pypdf`
  hvis det er installert, ellers får du en installasjonshint.

### Modellene er IKKE i repoet

`.pilot/models/` (~14 GB Ollama-blobs) og `.pilot/ollama/` (serverbinæret) er
utelatt i `.gitignore`. Hent dem selv:

```bash
# Med en vanlig Ollama-installasjon:
ollama pull qwen3.5:4b-mlx
ollama serve

# ...eller bruk en bundlet server i prosjektmappa:
OLLAMA_MODELS="$PWD/.pilot/models" .pilot/ollama/ollama serve
```

Pek `OLLAMA_URL` mot riktig port hvis du ikke bruker standarden `11434`.

---

## Kom i gang

```bash
# 1) Digest én fil med et fokusspørsmål
./digest.sh -q "hvilken enhet har DOSEVOLUM-registeret?" docs/pumpdriver-manual.pdf

# 2) Digest en hel mappe eller pipet output
./digest.sh firmware/*.h
dmesg | ./digest.sh -

# 3) Varm cachen i bakgrunnen først (valgfritt, gjør senere spørringer raske)
./digest_prewarm.sh docs/pumpdriver-manual.pdf &

# 4) Bygg den eager indeksen for hele arbeidsrommet
./digest_index.sh build . --summarize

# 5) Slå opp én fil (FRESH / STALE / MISS) og les kun det relevante utsnittet
./digest_index.sh lookup task_aquarack_v3 docs/pumpdriver-manual.pdf
./digest_index.sh slice task_aquarack_v3/docs/pumpdriver-manual.pdf --pages 12-14
```

Indeksen havner i `.dsh/digest/` og er gitignorert — den er lokal cache, ikke
kildekode.

---

## Slik virker det

### De tre nivåene i én indeks

1. **Strukturelle ankere — ingen LLM, deterministisk, bygges alltid.**
   Seksjonsoverskrifter, `#define`/tildelingsidentifikatorer, hex-adresser
   (`0x0020`) og verdi+enhet-tokens (`0,1 ml`). Dette er billige *pekere* inn i
   råfilen. For PDF-er er uttrekket sidebevisst (`pdf_pages.py`): hvert anker
   bærer siden sin, så leseren kan hente ut nøyaktig den ene siden et faktum
   ligger på i stedet for hele dokumentet.
2. **Map-reduce LLM-sammendrag — valgfritt (`--summarize`), strukturuavhengig.**
   For filer over `--summarize-min` (40 KB) kuttes teksten i
   kontekststørrelses-chunks med overlapp (`--chunk-tokens`, standard 60000;
   `--overlap-tokens`, standard 2000), hver chunk oppsummeres av den lokale
   modellen, og alle delsummene settes sammen til ett dokument. Ingen
   avhengighet til overskrifter — det virker på hvilken som helst PDF.
3. **Fokusert digest — ikke her.** Fortsatt `digest.sh`, men materialet er nå
   cachet av `prewarm.py`, og indeksen sier *hvor* du skal lete.

**Lesestien for den virkelige modellen:** slå opp kortet → svarer ankere eller
sammendraget? ferdig → ellers les kun det pekte utsnittet → ellers fokusert digest.

### Invalidering

Hvert kort er nøklet på filens **innholdshash** (`sha256`). `lookup` hasher
filen på nytt og nekter å bruke et kort hvis hashen ikke lenger stemmer:

```console
$ ./digest_index.sh lookup task_aquarack_v3 docs/pumpdriver-manual.pdf
digest-index: FRESH docs/pumpdriver-manual.pdf

$ # ...rediger filen...

$ ./digest_index.sh lookup task_aquarack_v3 docs/pumpdriver-manual.pdf
digest-index: STALE (content changed, hash ...): docs/pumpdriver-manual.pdf   # exit 1
```

En utdatert oppsummering blir **aldri** returnert.

### Prefix-cache-trikset

`digest_call.py` sender alltid materialet som en stabil prefix og det variable
fokusspørsmålet som en kort hale. `prewarm.py` bygger nøyaktig det samme
materialet byte-for-byte og sender én seed-request (system + MATERIAL, uten
spørsmål). Da blir den dyre prefilledelen et cache-treff når spørringen kommer.

---

## Eval: AquaRack

De tre `task_aquarack*`-mappene er en kontrollert oppgave i feilsøking av
innebygd firmware: en ESP32-S3-doseringshub gir alle fire pumpene 10× for lite
næring. Fasiten ligger i `.pilot/FASIT_aquarack*.md` med scoringsskjema (7 poeng).

Poenget er å måle **fidelitet per token**: hver oppgave har to prompt-varianter
som løser nøyaktig samme problem.

- **Variant A** (`PROMPT_A_kun_deepseek.md`) — modellen har full filtilgang og må
  ekstrahere og lese 40-siders databladet selv.
- **Variant B** (`PROMPT_B_deepseek_med_digest.md`) — modellen har i tillegg
  `digest.sh` som verktøy og kan delegere lesingen.

Vanskelighetsgraden trappes opp: i v1 ligger feilen i koden, i v2 skjules den av
en lokal `#undef`-overstyring i en senere `#include`, og i v3 finnes den riktige
faktoren **kun** i PDF-databladet — koden og arkivkopien har begge samme feil.
Databladet beskriver mange registre med ulike enheter (0,1 ml, 0,01 L/min,
0,1 °C, 1 hPa, 0,001 S/m), så modellen må disambiguere til det registeret som
faktisk gjelder.

Detaljer og eksakt forventet svar ligger i `OPPGAVE.md` og `README.md` i hver
oppgavemappe.

---

## Miljøvariabler

| Variabel | Standard | Gjelder |
|---|---|---|
| `OLLAMA_URL` | `http://127.0.0.1:11434` | alle |
| `DIGEST_MODEL` | `qwen3.5:4b-mlx` | alle |
| `DIGEST_TIMEOUT` | `60` | digest |
| `DIGEST_NUM_CTX` | `65536` | alle |
| `DIGEST_KEEP_ALIVE` | `30m` | alle |
| `DIGEST_INDEX_DIR` | `.dsh/digest` | indeks |
| `DIGEST_SEED_TIMEOUT` | `900` | prewarm |

Kjørt med `-h` på hvilket som helst av skriptene for full optionliste.

---

## Hva som ikke er i repoet

Utelatt i `.gitignore`, med vilje:

- **Modellvekter og serverbinær** — `.pilot/models/` (~14 GB), `.pilot/ollama/`.
- **Generert cache** — `.dsh/`, `.pilot/tmp/`, `logg- og .ready-filer`.
- **Tredjepartskode** — `.pilot/vendor/` (pypdf, `typing_extensions`); installer
  med `pip install pypdf`.
- **Private arbeidsdata** — `session.jsonl`, `token_spend_*.csv`, og
  `.pilot/home/` som inneholder en Ollama-nøkkel.
- **Opphavsrettslig materiale** — en fagartikkel og en skriveguide i PDF, som
  ikke er vår lisens å videreformidle.

De syntetiske databladene i `task_aquarack*/docs/` er generert av
`.pilot/gen_pdf_v3.py` og er en del av prosjektet.

---

## Lisens

Ingen lisens er lagt ved ennå — alt er «alle rettigheter forbeholdt» inntil
eieren velger en. Legg gjerne til en `LICENSE` før videre bruk.
