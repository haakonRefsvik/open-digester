# Prompt-variant A (v2) — KUN deepseek (full filtilgang)

> Lim inn i ny samtale med filverktøy (lese/grep/sed/find/pdf). Ingen digest.

---

Du er en feilsøker for innebygd firmware. Finn rotårsaken til at `AquaRack`
(ESP32-S3, Modbus RS-485, 4 pumper) gir plantene i rack 4 ~10× for lite næring
(planlagt 12,5 ml, faktisk ~1,25 ml).

Repo: `task_aquarack_v2/`. Orienter deg i treet selv (ls/find). Det finnes en
aktiv sketch-mappe og en arkivmappe (bare den aktive kompileres — Arduino-regel).
Mistenkelig: den aktive `config.h` SER ut til å ha riktig skalering, men enheten
doserer likevel feil — og det kan finnes FLERE definisjoner av samme symbol, i
tillegg til `#undef`. Inkluderingsrekkefolgen i .ino-en er avgjørende.

Bruk grep (grep -rn) og sed (sed -n 'A,Bp'), les docs/pumpdriver-manual.pdf
(autoritativt), og sjekk logs/serial_log_2026-09-01.txt.

Lever:
1. Eksakt rotårsak: symbol, faktisk gjeldende verdi ved kompilering, og hvorfor
   den overskygger den andre definisjonen.
2. Bevis: grep/sed-funn (inkl. include-rekkefolge), PDF-funn, logg-funn.
3. Fiks (konkret endring) og hvorfor arkivkopien er irrelevant.

Ikke endre filer — bare diagnoser. Svar kort og presist.
