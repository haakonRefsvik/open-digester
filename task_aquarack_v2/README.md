# AquaRack v2 — doseringshub med LOKAL OVERSTYRING (eval-oppgave)

ESP32-S3-basert hydroponisk doseringshub som styrer 4 peristaltiske pumper over
Modbus RS-485, leser EC/pH, og sender en time-rapport over TLS.

## Struktur

```
task_aquarack_v2/
├── firmware/
│   ├── AquaRack/          # AKTIV sketch (kompileres)
│   │   ├── AquaRack.ino   #   inkluderer config.h, SA config_local.h
│   │   ├── config.h       #   DOSE_SCALE_ML = 10 (korrekt)
│   │   ├── config_local.h #   LOKAL OVERSTYRING: #undef + #define 1
│   │   └── modbus.h
│   └── Arkiv/2026-06/     # ARKIVERT (egen sketch, IKKE bygget)
│       ├── AquaRack.ino
│       └── config.h       #   DOSE_SCALE_ML = 10
├── logs/
│   └── serial_log_2026-09-01.txt
└── docs/
    └── pumpdriver-manual.pdf       # registeret er i 0,1 ml -> x10
```

**Arduino-regelen som gjelder her:** sketch-mappen må hete det samme som
`.ino`-filen, og alt i mappen kompileres som én oversettingsenhet — inkludert
alle `.h` som `.ino`-en trekker inn. Inkluderingsrekkefolgen betyr noe: en
senere `#include` med `#undef` overskriver en tidligere `#define`.

## Rapportert symptom

Plantene i rack 4 får for lite næring. Dosepumpene kjører hver time, men dosen
som faktisk pumpes er ~10× for liten (planlagt 12,5 ml -> ~1,25 ml). Merk:
`config.h` SER korrekt ut (skala 10) — likevel doseres det feil.
