# OPPGAVE — AquaRack v3 doserer 10x for lite (fasiten star i databladet)

Doseringshubben `AquaRack` gir alle fire pumpene ~10x for lite næring
(planlagt 12,5 / 12,5 / 7,0 / 7,0 ml, faktisk ~1,25 / 1,25 / 0,7 / 0,7 ml).

Mistenkelig detalj: `firmware/AquaRack/config.h` definerer `DOSE_SCALE_ML = 1`.
Den riktige faktoren star IKKE i koden — hverken i den aktive sketchen eller i
`Arkiv/` (som har samme verdi, eldre revisjon). Den star kun i
`docs/pumpdriver-manual.pdf` (40 sider datablad), som definerer registerets
enhet.

Arbeid i repoet `task_aquarack_v3/`. Du har grep, sed, PDF-uttrekker og
ls/find. Merk at databladet beskriver MANGE registre med ulike enheter
(0,1 ml, 0,01 L/min, 0,1 grader C, 1 hPa, 0,001 S/m) — du ma finne den som
gjelder DOSEVOLUM-registeret (0x0020..0x0023).

**Krav til leveransen:**
1. Identifiser den eksakte rotarsaken: hvilket symbol, hvilken verdi som faktisk
   gjelder, og hvilken verdi den SKULLE hatt.
2. Vis bevis fra koden (grep/sed) OG fra databladet (den relevante enheten), OG
   fra loggen (registerverdiene som faktisk ble skrevet).
3. Gi fiks-en (konkret endring) og forklar hvorfor arkivkopien ikke hjelper.

Svar kort og presist. Ikke endre filer; bare diagnoser.
