# Prompt-variant A — KUN deepseek (full filtilgang)

> Lim dette inn i en ny samtale der modellen har verktøytilgang til
> filsystemet (lese/grep/sed/find/pdf-ekstraksjon). Ingen digest.sh involvert.

---

Du er en feilsøker for innebygd firmware. Du skal finne rotårsaken til at
doseringshubben `AquaRack` (ESP32-S3, Modbus RS-485, 4 peristaltiske pumper)
gir plantene i rack 4 for lite næring: dosen som pumpes ser ut til å være ~10×
for liten (planlagt 12,5 ml, faktisk ~1,25 ml).

Repoen ligger i mappen `task_aquarack/` i arbeidskatalogen. Orienter deg i
filstrukturen selv (ls/find). Merk at det finnes BÅDE en aktiv sketch-mappe og
en arkivmappe — bare den aktive kompileres (Arduino-regelen: sketch-mappen må
hete det samme som .ino-filen).

Bruk grep (grep -rn) og sed (sed -n 'A,Bp') på kildefilene, les
docs/pumpdriver-manual.pdf (Modbus-registerkartet er autoritativt), og sjekk
logs/serial_log_2026-09-01.txt for bevis på hva enheten faktisk gjorde.

Lever:
1. Eksakt rotårsak (konstant + verdi + fil).
2. Bevis: grep/sed-funn, PDF-funn, logg-funn.
3. Fiks (konkret endring) og hvorfor arkivkopien IKKE er relevant.

Ikke endre filer — bare diagnoser. Svar kort og presist.
