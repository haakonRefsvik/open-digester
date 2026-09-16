# Prompt-variant B — deepseek MED digest som verktøy

> Samme oppgave som variant A. Forskjellen: du har EKSTRA tilgang til
> `digest.sh` for å oppsummere innholdet i enkeltfiler raskt, i stedet for å
> lese dem selv.

---

Du er en feilsøker for innebygd firmware. Du har FULL filtilgang: `ls`, `find`,
`grep -rn`, `sed -n 'A,Bp'`, lesing og PDF-ekstraksjon — som vanlig.

I TILLEGG har du dette verktøyet:

```
./digest.sh -m gemma4:12b-mlx -q "SPØRSMÅL OM FILEN" STI/TIL/FIL
```

`digest.sh` leser ÉN fil (eller PDF, som den ekstraherer selv) og returnerer en
kort, komprimert oppsummering som svarer på spørsmålet ditt. Bruk det når du må
forstå innholdet i en stor fil raskere enn å lese den selv — f.eks. en PDF eller
en lang logg. Du bestemmer selv når det lønner seg; grep/sed er fortsatt riktig
verktøy for å finne *hvor* ting er.

Oppgave: finn rotårsaken til at `AquaRack` (ESP32-S3, Modbus RS-485, 4 pumper)
gir plantene i rack 4 ~10× for lite næring (planlagt 12,5 ml, faktisk ~1,25 ml).

Repo: `task_aquarack/`. Det finnes en aktiv sketch-mappe og en arkivmappe; bare
den aktive kompileres (Arduino-regel).

Lever:
1. Eksakt rotårsak (konstant + verdi + fil).
2. Bevis: grep/sed-funn + det du lærte av PDF-en og loggen.
3. Fiks (konkret endring) og hvorfor arkivkopien ikke er relevant.

Ikke endre filer — bare diagnoser. Svar kort og presist.
