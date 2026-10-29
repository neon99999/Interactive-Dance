// IMU: Adafruit LSM6DS3TR-C accelerometer + gyroscope over I2C.
// Talks to the sensor's registers directly (no library). begin() scans the I2C
// bus, finds the sensor at 0x6A or 0x6B and configures it; update() reads it at
// IMU_READ_MS and prints a reading every IMU_LOG_MS as a name=value line that
// the TouchDesigner serial input reads. If the sensor is missing it retries
// every IMU_RETRY_MS, so a loose wire can be fixed without a reset.
#pragma once

#include <stdint.h>

namespace imu {

struct Reading {
  float ax, ay, az;  // acceleration in g
  float gx, gy, gz;  // rotation in degrees per second
  uint32_t timeMs;   // millis() when read
};

bool begin();
void update();

bool isReady();
uint8_t address();        // I2C address in use, 0 when not found
const Reading& latest();  // last reading; timeMs is 0 before the first one

}  // namespace imu
