# OPPGAVE — AquaRack doserer for lite

Du skal finne rotårsaken til at doseringshubben `AquaRack` gir plantene i rack 4
for lite næring. Rapportert: dosen som pumpes ser ut til å være ~10× for liten
(planlagt 12,5 ml, faktisk ~1,25 ml).

Arbeid i repoet `task_aquarack/`. Du har disse verktøyene tilgjengelig:
- `grep` (med `-rn`) for å søke i kildefiler
- `sed -n 'A,Bp'` for å dumpe linjeintervaller
- en PDF-uttrekker for `docs/*.pdf`
- `ls`/`find` for orientering i filtreet

**Krav til leveransen:**
1. Identifiser den eksakte rotårsaken (hvilken konstant, hvilken verdi, i hvilken fil).
2. Vis beviset fra koden (grep/sed-funn), fra PDF-en, og fra serial-loggen.
3. Gi fiks-en (konkret endring), og forklar hvorfor den aktive filen — ikke arkivkopien — er den som må endres.

Svar kort og presist. Ikke endre filer; bare diagnoser.
