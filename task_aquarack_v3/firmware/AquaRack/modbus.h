#ifndef MODBUS_H
#define MODBUS_H

#include <Arduino.h>

void modbusInit();
bool modbusWriteRegister(uint8_t addr, uint16_t reg, uint16_t value);

#endif // MODBUS_H
