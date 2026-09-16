# Prompt-variant B (v3) — deepseek MED digest som verktøy

> Samme oppgave som variant A. Forskjellen: du har EKSTRA tilgang til
> `digest.sh` som et verktøy for å oppsummere innholdet i enkeltfiler raskt
> (typisk PDF-er og store logger), i stedet for å lese dem selv.

---

Du er en feilsøker for innebygd firmware. Du har FULL filtilgang: du kan bruke
`ls`, `find`, `grep -rn`, `sed -n 'A,Bp'`, lese filer og ekstrahere PDF-er —
akkurat som vanlig.

I TILLEGG har du dette verktøyet til disposisjon:

```
./digest.sh -q "SPØRSMÅL OM FILEN" STI/TIL/FIL
```

`digest.sh` leser ÉN fil (eller PDF, som den ekstraherer selv) og returnerer en
kort, komprimert oppsummering som svarer på spørsmålet ditt (standardmodell
`qwen3.5:4b-mlx`). Bruk det når du ma forstå innholdet i en stor fil raskere
enn å lese den selv — f.eks. en PDF eller en lang logg. Du bestemmer selv når
det lønner seg; grep/sed er fortsatt riktig verktøy for å finne *hvor* ting er.

`digest.sh` er cappet på 60 sekunder. Hvis den bruker lenger, avbrytes den og
returnerer feilkode 124 (`digest: TIMEOUT ...`) — da leser du bare filen direkte
selv med dine vanlige verktøy i stedet.

Oppgave: finn rotårsaken til at `AquaRack` (ESP32-S3, Modbus RS-485, 4 pumper)
gir alle pumpene ~10x for lite næring (planlagt 12,5 / 12,5 / 7,0 / 7,0 ml,
faktisk ~1,25 / 1,25 / 0,7 / 0,7 ml).

Repo: `task_aquarack_v3/`. Den aktive `config.h` har `DOSE_SCALE_ML = 1`, og
arkivkopien har samme verdi — den riktige faktoren star IKKE i koden, men i
`docs/pumpdriver-manual.pdf` (40 sider datablad) som definerer registerets
ENHET. Databladet beskriver mange registre med ulike enheter (0,1 ml,
0,01 L/min, 0,1 grader C, 1 hPa, ...) — du ma finne den som gjelder
DOSEVOLUM-registeret (0x0020..0x0023).

Lever:
1. Eksakt rotarsak: symbol, faktisk verdi, og verdien den SKULLE hatt.
2. Bevis (grep/sed + det du lærte av databladet og loggen).
3. Fiks (konkret endring) og hvorfor arkivkopien ikke hjelper.

Ikke endre filer — bare diagnoser. Svar kort og presist.
