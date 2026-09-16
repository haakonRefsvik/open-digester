/*
 * AquaRack — doseringshub for hydroponisk rack (ESP32-S3 + Modbus RS-485).
 *
 * Styrer 4 peristaltiske pumper over Modbus, leser EC/pH, og sender en
 * statusrapport over TLS til en ekstern "dash"-kanal hver time.
 *
 * VIKTIG (Arduino-krav): sketch-mappen MÅ hete det samme som .ino-filen.
 * Hele enheten (denne filen + alle .h som inkluderes) kompileres som ÉN
 * oversettingsenhet.
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include "config.h"
#include "modbus.h"

// ---------------------------------------------------------------------------
// Doseringslogikk
// ---------------------------------------------------------------------------
//
// Pumpe-driveren (se docs/pumpdriver-manual.pdf) eksponerer dose-volumet som
// et 16-bit Modbus-register. Volumet vi sender = ønsket_ml * DOSE_SCALE_ML.
// Tallet må havne i riktig ENHET for registeret, ellers doserer vi feil.
// Databladet definerer enheten — ikke denne filen.
static void sendDose(uint8_t pump, float ml) {
  uint16_t reg = (uint16_t)(ml * DOSE_SCALE_ML);
  if (reg > 65535) reg = 65535;
  modbusWriteRegister(MODBUS_ADDR_PUMP, MODBUS_REG_DOSE_BASE + pump, reg);
  Serial.printf("[dose] pumpe %u: %.1f ml -> register %u\n", pump, ml, reg);
}

// ---------------------------------------------------------------------------
// Opplastning av time-rapport (TLS).
// ---------------------------------------------------------------------------
static bool uploadReport(const char *body) {
  WiFiClientSecure client;
  client.setTimeout(DASH_WRITE_TIMEOUT_S);
  if (!client.connect(DASH_HOST, 443, DASH_CONNECT_TIMEOUT_MS)) {
    Serial.println("[dash] FEIL: TLS-tilkobling feilet");
    return false;
  }
  client.print("POST /report HTTP/1.1\r\nHost: " DASH_HOST "\r\n");
  client.print("Content-Type: application/json\r\n");
  client.print("Content-Length: " + String(strlen(body)) + "\r\n\r\n");
  client.print(body);
  delay(100);
  while (client.connected() && client.available() == 0) { delay(10); }
  String line = client.readStringUntil('\n');
  Serial.printf("[dash] svar: %s\n", line.c_str());
  client.stop();
  return line.startsWith("HTTP/1.1 200");
}

static uint32_t lastDoseMs = 0;
static uint32_t lastReportMs = 0;

void setup() {
  Serial.begin(115200);
  modbusInit();
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.println("[boot] AquaRack oppe");
}

void loop() {
  uint32_t now = millis();

  if (now - lastDoseMs >= DOSE_INTERVAL_MS) {
    lastDoseMs = now;
    const float plan[4] = {12.5f, 12.5f, 7.0f, 7.0f};
    for (uint8_t i = 0; i < 4; i++) {
      sendDose(i, plan[i]);
    }
  }

  if (now - lastReportMs >= REPORT_INTERVAL_MS) {
    lastReportMs = now;
    String body = "{\"type\":\"status\",\"rack\":\"" RACK_ID "\"}";
    uploadReport(body.c_str());
  }
}
