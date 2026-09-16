# FASIT (skjult) — AquaRack v2 doserer for lite (shadow-felle)

## Rotårsak

`DOSE_SCALE_ML` er definert to ganger i den aktive sketchen:
- `firmware/AquaRack/config.h`        -> `#define DOSE_SCALE_ML 10`  (korrekt)
- `firmware/AquaRack/config_local.h`  -> `#undef DOSE_SCALE_ML` + `#define DOSE_SCALE_ML 1`  (FEIL)

`.ino`-en inkluderer `config.h` FØRST og `config_local.h` ETTERTID. Siden
`config_local.h` gjør `#undef` og så redefinerer, er den GJELDENDE verdien ved
kompilering `1` — ikke `10`. Derfor skrives 12,5 ml som register `12` (=~1,25 ml),
altså 10× for lite, selv om `config.h` ser korrekt ut.

## Beviskjeden (krever KRYSS av tre filer)

1. `config.h` alene: `DOSE_SCALE_ML = 10` — ser RIKTIG ut. (fellen)
2. `config_local.h`: `#undef DOSE_SCALE_ML` + `#define DOSE_SCALE_ML 1`.
3. `.ino`: `#include "config.h"` (linje A) SÅ `#include "config_local.h"` (linje B)
   -> rekkefolgen er det som lar #undef vinne. `sendDose` bruker `ml * DOSE_SCALE_ML`.
4. PDF: registeret i 0,1 ml -> x10 (autoritativ; finnes bare her).
5. Logg: `12.5 ml -> register 12`, `7.0 ml -> register 7` (skulle vært 125/70)
   -> beviser at den GJELDENDE faktoren er 1, ikke 10.

## Fiks

Fjern (eller rett) den lokale overstyringen i `firmware/AquaRack/config_local.h`:
enten slett `#undef`/`#define DOSE_SCALE_ML 1`-paret, eller slett `#include
"config_local.h"` fra `.ino`-en. Da arver bygget `DOSE_SCALE_ML = 10` fra config.h.

## Hvorfor arkivkopien IKKE er relevant

`firmware/Arkiv/2026-06/` er egen mappe med egen `.ino` -> egen separat
Arduino-sketch som aldri kompileres sammen med den aktive. Dens `config.h = 10`
er irrelevant for det aktive bygget.

## Scoring (begge kjøringer)

| Kriterium | Poeng |
|---|---|
| Riktig symbol (`DOSE_SCALE_ML`) | 1 |
| Riktig GJELDENDE verdi (`1`, via config_local.h #undef) | 1 |
| Identifisert config_local.h som overstyrende fil | 1 |
| Forklart at include-rekkefolge + #undef er hvorfor den vinner | 1 |
| Sitert PDF (0,1 ml / x10) | 1 |
| Sitert logg-bevis (register 12/7) | 1 |
| Forklart arkivkopiens irrelevans | 1 |
| **Total** | **7** |

## Det som skiller A fra B

Kjernen er en cross-file-kjensgjerning: "det finnes TO definisjoner og #undef +
include-rekkefolgen gjør at 1 vinner". Den finnes ikke i noen ENKELT fil — den
krever at config.h + config_local.h + .ino leses SAMMEN. Punkt-briefs per fil
kan ikke formidle "hvilken verdi som faktisk gjelder ved kompilering" med mindre
en av briefene eksplisitt rapporterer include-rekkefolgen OG #undef. A (grep/find)
far dette gratis; B (digest) ma ha det inn i briefene.
