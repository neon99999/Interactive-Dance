// IMU: Adafruit LSM6DS3TR-C accelerometer + gyroscope over I2C.
// Talks to the sensor's registers directly (no library). begin() scans the I2C
// bus, finds the sensor at 0x6A or 0x6B and configures it; update() polls it
// every IMU_READ_MS and returns true when it read a new sample. If the sensor
// is missing it retries every IMU_RETRY_MS, so a loose wire can be fixed
// without a reset.
#pragma once

#include <stdint.h>

namespace imu {

struct Reading {
  float ax, ay, az;  // acceleration in g
  float gx, gy, gz;  // rotation in degrees per second
  uint32_t timeMs;   // millis() when read
  uint32_t timeUs;   // micros() when read, for the time between samples
};

bool begin();
bool update();  // true when a new sample was read

bool isReady();
uint8_t address();        // I2C address in use, 0 when not found
const Reading& latest();  // last reading; timeMs is 0 before the first one

}  // namespace imu
