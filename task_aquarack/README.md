# AquaRack — doseringshub (eval-oppgave)

ESP32-S3-basert hydroponisk doseringshub som styrer 4 peristaltiske pumper over
Modbus RS-485, leser EC/pH, og sender en time-rapport over TLS.

## Struktur

```
task_aquarack/
├── firmware/
│   ├── AquaRack/          # AKTIV sketch (kompileres)
│   │   ├── AquaRack.ino
│   │   ├── config.h
│   │   └── modbus.h
│   └── Arkiv/2026-06/     # ARKIVERT (egen mappe = egen sketch, IKKE bygget)
│       ├── AquaRack.ino
│       └── config.h
├── logs/
│   └── serial_log_2026-09-01.txt   # seriell-dump fra enheten
└── docs/
    └── pumpdriver-manual.pdf       # PM-4 Modbus-registerkart (autoritativ)
```

**Arduino-regelen som gjelder her:** sketch-mappen må hete det samme som
`.ino`-filen, og alt i mappen kompileres som én oversettingsenhet. Filer i andre
mapper (f.eks. `Arkiv/`) er ikke en del av bygget.

## Rapportert symptom

Plantene i rack 4 får for lite næring. Dosepumpene kjører hver time, men
vekstmediet tørker ut og EC faller jevnt — alt tyder på at dosen som faktisk
pumpes er en brøkdel av det som er planlagt (12,5 ml → ser ut som ~1,25 ml).
