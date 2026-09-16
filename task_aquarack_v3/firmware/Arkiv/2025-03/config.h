#ifndef CONFIG_H
#define CONFIG_H

// =====================
// Nettverk / dash  (revisjon 2025-03 — eldre, IKKE aktiv)
// =====================
#define WIFI_SSID               "rack-wifi-1g"
#define WIFI_PASS               "gammeltpassord"
#define DASH_HOST               "dash-old.aquarack.example"
#define RACK_ID                 "rack-4"

#define DASH_CONNECT_TIMEOUT_MS 30000UL
#define DASH_WRITE_TIMEOUT_S    60

#define DOSE_INTERVAL_MS        3600000UL
#define REPORT_INTERVAL_MS      3600000UL

// Skala-faktor (revisjon 2025-03). Merk: denne gamle verdien var også 1 —
// feilen er med andre ord eldre enn den ser ut til, og finnes ikke i koden.
#define DOSE_SCALE_ML           1

#define MODBUS_ADDR_PUMP        0x01
#define MODBUS_REG_DOSE_BASE    0x0020

#endif // CONFIG_H
