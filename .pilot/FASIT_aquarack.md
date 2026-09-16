# FASIT (skjult) — AquaRack doserer for lite

## Rotårsak

`DOSE_SCALE_ML` er `1` i den AKTIVE filen
`firmware/AquaRack/config.h`, men pumpe-registeret er i **0,1 ml**, så ml må
ganges med **10** (jf. `docs/pumpdriver-manual.pdf`). Med faktor 1 skrives
12,5 → register 12 (≈1,25 ml reelt), altså 10× for lite.

## Beviskjedene

1. **grep** (`grep -rn DOSE_SCALE_ML firmware/`) gir TREFF i to filer:
   - `firmware/AquaRack/config.h` → `1` (aktiv, FEIL)
   - `firmware/Arkiv/2026-06/config.h` → `10` (arkivert, RIKTIG verdi)
   Dette er fellen: den riktige verdien finnes, men i en mappe som IKKE bygges.

2. **sed** på aktiv config bekrefter kontekst:
   `sed -n '/DOSE_SCALE_ML/p' firmware/AquaRack/config.h` → `#define DOSE_SCALE_ML 1`
   Og i .ino-en: `sed -n '38,46p' firmware/AquaRack/AquaRack.ino` viser
   `reg = ml * DOSE_SCALE_ML` — skaleringen er aktiv, bare faktoren er feil.

3. **PDF** (`docs/pumpdriver-manual.pdf`) er AUTORITATIV og finnes ikke i koden:
   "DOSEVOLUM-REGISTERET ER I 0,1 MILLILITER ... gange onsket ml med 10."
   Dette er eneste sted enheten/faktoren står.

4. **Logg** (`logs/serial_log_2026-09-01.txt`): `pumpe 0: 12.5 ml -> register 12`
   og `pumpe 2: 7.0 ml -> register 7` — bekrefter at registeret = ml × 1,
   ikke ml × 10 (skulle vært 125 og 70).

## Fiks

Endre i `firmware/AquaRack/config.h`:
```c
#define DOSE_SCALE_ML           10
```

## Hvorfor arkivkopien IKKE er relevant

`firmware/Arkiv/2026-06/` er en egen mappe med egen `.ino` → en egen,
separat Arduino-sketch. Den kompileres aldri sammen med den aktive sketchen i
`firmware/AquaRack/`. Å "fikse" arkiv-filen endrer ingenting; den riktige
verdien står der kun som et historisk spor.

## Scoring (begge kjøringer)

| Kriterium | Poeng |
|---|---|
| Riktig konstant (`DOSE_SCALE_ML`) | 1 |
| Riktig verdi (`1` er feil, skal være `10`) | 1 |
| Riktig fil (aktiv `AquaRack/config.h`, ikke Arkiv) | 1 |
| Sitert PDF som autoritativ kilde for 0,1 ml / ×10 | 1 |
| Sitert logg-bevis (register 12/7) | 1 |
| Forklart hvorfor Arkiv-kopien ikke bygges | 1 |
| **Total** | **6** |

## Forventet grep/sed-kommandoer en god agent bruker

```bash
find task_aquarack -name config.h           # avslorer TO config.h -> fellen
grep -rn DOSE_SCALE_ML task_aquarack/firmware/
sed -n '30,40p' task_aquarack/firmware/AquaRack/config.h
sed -n '30,40p' task_aquarack/firmware/AquaRack/AquaRack.ino
python3 .pilot/pdf_extract.py task_aquarack/docs/pumpdriver-manual.pdf
grep -n "register" task_aquarack/logs/serial_log_2026-09-01.txt
```
