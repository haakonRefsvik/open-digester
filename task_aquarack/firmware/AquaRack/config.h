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
#define DASH_CONNECT_TIMEOUT_MS 30000UL
#define DASH_WRITE_TIMEOUT_S    60

// =====================
// Doserings- og sensor-plan
// =====================
#define DOSE_INTERVAL_MS        3600000UL   // doser hver time
#define REPORT_INTERVAL_MS      3600000UL   // rapport hver time

// SKALA-FAKTOR for pumpe-registeret. Se docs/pumpdriver-manual.pdf for enheten.
// Ønsket volum (ml) ganges med denne før det skrives til Modbus-registeret.
#define DOSE_SCALE_ML           1

// Modbus-adresser.
#define MODBUS_ADDR_PUMP        0x01
#define MODBUS_REG_DOSE_BASE    0x0020      // pumpe 0..3 -> 0x20..0x23

#endif // CONFIG_H
