# AquaRack v3 — skaleringskonstanten er feil, og fasiten star bare i databladet

ESP32-S3-basert hydroponisk doseringshub som styrer 4 peristaltiske pumper over
Modbus RS-485, leser EC/pH, og sender en time-rapport over TLS.

## Struktur

```
task_aquarack_v3/
├── firmware/
│   ├── AquaRack/          # AKTIV sketch (kompileres)
│   │   ├── AquaRack.ino
│   │   ├── config.h       #   DOSE_SCALE_ML = 1  (mistenkelig)
│   │   └── modbus.h
│   └── Arkiv/2025-03/     # ARKIVERT (egen sketch, IKKE bygget)
│       ├── AquaRack.ino
│       └── config.h       #   DOSE_SCALE_ML = 1  (samme verdi, eldre rev)
├── logs/
│   └── serial_log_2026-09-01.txt      # 126 KB, repeterende sensor/heartbeat
└── docs/
    └── pumpdriver-manual.pdf          # 40 sider datablad — registerets ENHET
                                       # (0,1 ml -> x10) star bare HER
```

**Arduino-regelen:** sketch-mappen må hete det samme som `.ino`-filen, og alt i
mappen kompileres som én oversettingsenhet. Mapper utenfor (Arkiv/) er egne
sketcher og kompileres ikke.

## Rapportert symptom

Alle fire dosepumpene gir ~10x for lite næring (planlagt 12,5 / 12,5 / 7,0 /
7,0 ml, faktisk ~1,25 / 1,25 / 0,7 / 0,7 ml). Det finnes ingen arkivkopi med
riktig verdi og ingen `#undef`-felle — den riktige faktoren star kun i
databladet (40 sider), der enhetsfeilen er dokumentert.
