# Prompt-variant A (v3) — KUN deepseek (full filtilgang)

> Lim inn i ny samtale med filverktøy (lese/grep/sed/find/pdf). Ingen digest.

---

Du er en feilsøker for innebygd firmware. Finn rotårsaken til at `AquaRack`
(ESP32-S3, Modbus RS-485, 4 pumper) gir alle pumpene ~10x for lite næring
(planlagt 12,5 / 12,5 / 7,0 / 7,0 ml, faktisk ~1,25 / 1,25 / 0,7 / 0,7 ml).

Repo: `task_aquarack_v3/`. Orienter deg i treet selv (ls/find). Det finnes en
aktiv sketch-mappe og en arkivmappe (bare den aktive kompileres — Arduino-regel).
Den aktive `config.h` har `DOSE_SCALE_ML = 1`, og arkivkopien har samme verdi —
den riktige faktoren star IKKE i koden, men i `docs/pumpdriver-manual.pdf`
(40 sider datablad) som definerer registerets ENHET. Databladet beskriver mange
registre med ulike enheter (0,1 ml, 0,01 L/min, 0,1 grader C, 1 hPa, ...) — du
ma finne den som gjelder DOSEVOLUM-registeret (0x0020..0x0023).

Bruk grep (grep -rn) og sed (sed -n 'A,Bp'), ekstraher og les
docs/pumpdriver-manual.pdf (autoritativt), og sjekk
logs/serial_log_2026-09-01.txt.

Lever:
1. Eksakt rotarsak: symbol, faktisk verdi, og verdien den SKULLE hatt.
2. Bevis: grep/sed-funn, PDF-funn (enheten), logg-funn (registerverdiene).
3. Fiks (konkret endring) og hvorfor arkivkopien ikke hjelper.

Ikke endre filer — bare diagnoser. Svar kort og presist.

---

Svar kort og presist.
