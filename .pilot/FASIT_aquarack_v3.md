# FASIT (skjult) — AquaRack v3 doserer 10x for lite (fasit i databladet)

## Rotårsak

`firmware/AquaRack/config.h` definerer `#define DOSE_SCALE_ML 1`. Det er FEIL —
verdien skal være `10`.

Den riktige faktoren finnes IKKE i koden: hverken i den aktive sketchen eller i
`firmware/Arkiv/2025-03/config.h` (som ogsa har `DOSE_SCALE_ML 1`). Den star kun
i `docs/pumpdriver-manual.pdf`, avsnitt 4.3, som slar fast at dosevolum-
registeret (0x0020..0x0023) er i 0,1 ml og at firmware ma gange onsket ml med 10.

## Beviskjeden

1. `config.h`: `DOSE_SCALE_ML = 1` (grep -rn DOSE_SCALE_ML -> 1 i aktiv, 1 i arkiv).
2. `Arkiv/2025-03/config.h`: ogsa `1` -> arkivet bekrefter IKKE noen riktig
   verdi; det er en eldre revisjon med samme feil.
3. Databladet (PDF, avsnitt 4.3): "DOSEVOLUM-REGISTERET ER I 0,1 MILLILITER
   (en tiendedels ml)... gange onsket ml med 10". Mange andre registre har
   andre enheter (0,01 L/min for stromning, 0,1 grader C for temp, 1 hPa for
   trykk, 0,001 S/m for EC) — bare 0x0020..0x0023 er dosevolum.
4. Logg: `[dose] pumpe 0: 12.5 ml -> register 12` (skulle vært 125) og
   `7.0 ml -> register 7` (skulle vært 70) -> beviser at faktisk faktor er 1.

## Fiks

Endre `#define DOSE_SCALE_ML 1` til `#define DOSE_SCALE_ML 10` i
`firmware/AquaRack/config.h`.

## Hvorfor arkivkopien IKKE hjelper

`firmware/Arkiv/2025-03/` er egen mappe med egen `.ino` -> egen separat
Arduino-sketch som aldri kompileres. I tillegg har den samme feil (verdi 1),
sa selv om den hadde vært relevant, gir den ingen korrekt verdi.

## Scoring

| Kriterium | Poeng |
|---|---|
| Riktig symbol (`DOSE_SCALE_ML`) | 1 |
| Riktig faktisk verdi (`1`) | 1 |
| Riktig KORREKT verdi (`10`) | 1 |
| Kildet den til databladet (ikke koden) | 1 |
| Sitert PDF-enheten (0,1 ml -> x10) | 1 |
| Sitert logg-bevis (register 12/7, skulle vært 125/70) | 1 |
| Forklart arkivkopiens irrelevans (feil verdi + egen sketch) | 1 |
| **Total** | **7** |

## Hva skiller A fra B (token-sammenligning)

Databladet er 40 sider (~86 KB tekst, ~21 600 tokens). A ma ekstrahere og lese
(eller i beste fall ekstrahere + grep + disambiguere blant ~14 forekomster av
"0,1" knyttet til ulike registre). B kan delegere til digest med et fokusert
spørsmål og fa et ~200-tokens svar som direkte gir enheten. Det er her
besparelsen ligger — og fideliteten er 100 % fordi avsnitt 4.3 er presist
formulert.
