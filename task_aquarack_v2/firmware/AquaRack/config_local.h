#ifndef CONFIG_LOCAL_H
#define CONFIG_LOCAL_H

// =====================
// LOKAL OVERSTYRING — leses IKKE av alle. Se .ino for inkluderingsrekkefolge.
// =====================
// Midlertidig drypp-kalibrering (2026-08): en del av pumpene over-doserte med
// faktor 10, sa vi senket skaleringen midlertidig. Skal tilbake til config.h
// sin verdi nar kalibreringen er ferdig — men filen ble liggende i bygget.
#undef  DOSE_SCALE_ML
#define DOSE_SCALE_ML 1

#endif // CONFIG_LOCAL_H
