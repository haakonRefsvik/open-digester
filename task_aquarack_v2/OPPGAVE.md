# OPPGAVE — AquaRack v2 doserer for lite (til tross for at config.h ser riktig ut)

Du skal finne rotårsaken til at doseringshubben `AquaRack` gir plantene i rack 4
for lite næring. Rapportert: dosen som pumpes ser ut til å være ~10× for liten
(planlagt 12,5 ml, faktisk ~1,25 ml).

Mistenkelig detalj: den aktive `config.h` definerer tilsynelatende riktig
skalering — men enheten doserer likevel feil. Det finnes BÅDE en aktiv
sketch-mappe og en arkivmappe, og det kan finnes flere definisjoner av samme
symbol.

Arbeid i repoet `task_aquarack_v2/`. Du har grep, sed, PDF-uttrekker og ls/find.

**Krav til leveransen:**
1. Identifiser den eksakte rotårsaken (hvilket symbol, hvilken VERDI som faktisk
   gjelder ved kompilering, og HVORFOR den overskygger den andre).
2. Vis bevis fra koden (grep/sed-funn inkl. inkluderingsrekkefolge), PDF-en, og loggen.
3. Gi fiks-en (konkret endring) og forklar hvorfor arkivkopien ikke er relevant.

Svar kort og presist. Ikke endre filer; bare diagnoser.
