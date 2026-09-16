/*
 * AquaRack — revisjon 2025-03 (ARKIVERT, egen sketch-mappe -> kompileres IKKE).
 * Eldre versjon uten TLS-rapportering og uten EC/pH-polling.
 */

#include <WiFi.h>
#include "config.h"
#include "modbus.h"

static void sendDose(uint8_t pump, float ml) {
  uint16_t reg = (uint16_t)(ml * DOSE_SCALE_ML);
  modbusWriteRegister(MODBUS_ADDR_PUMP, MODBUS_REG_DOSE_BASE + pump, reg);
  Serial.printf("[dose] pumpe %u: %.1f ml -> register %u\n", pump, ml, reg);
}

void setup() {
  Serial.begin(115200);
  modbusInit();
  WiFi.begin(WIFI_SSID, WIFI_PASS);
}

void loop() {
  const float plan[4] = {12.5f, 12.5f, 7.0f, 7.0f};
  for (uint8_t i = 0; i < 4; i++) sendDose(i, plan[i]);
  delay(DOSE_INTERVAL_MS);
}
