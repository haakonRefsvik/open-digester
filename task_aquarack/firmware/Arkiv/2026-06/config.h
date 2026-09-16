#ifndef CONFIG_H
#define CONFIG_H

// =====================
// Nettverk / dash
// =====================
#define WIFI_SSID               "rack-wifi-2g"
#define WIFI_PASS               "h0stpassord"
#define DASH_HOST               "dash.aquarack.example"
#define RACK_ID                 "rack-4"

// TLS / opplastning timeouts (ms / s).
#define DASH_CONNECT_TIMEOUT_MS 20000UL   // eldre verdi
#define DASH_WRITE_TIMEOUT_S    30        // eldre verdi

// =====================
// Doserings- og sensor-plan
// =====================
#define DOSE_INTERVAL_MS        3600000UL
#define REPORT_INTERVAL_MS      3600000UL

// SKALA-FAKTOR for pumpe-registeret. Se docs/pumpdriver-manual.pdf for enheten.
// (KORRIGERT etter kalibrering 2026-06: registeret er i 0,1 ml, altså x10.)
#define DOSE_SCALE_ML           10

// Modbus-adresser.
#define MODBUS_ADDR_PUMP        0x01
#define MODBUS_REG_DOSE_BASE    0x0020

#endif // CONFIG_H
