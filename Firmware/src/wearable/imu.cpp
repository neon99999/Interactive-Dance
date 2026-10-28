#include "imu.h"

#include <Arduino.h>

#include "config.h"

namespace imu {

bool begin() {
  Serial.printf("[imu] placeholder: LSM6DS3TR-C expected at 0x%02X (SDA %d, SCL %d), not started\n",
                dance::IMU_I2C_ADDRESS, dance::PIN_I2C_SDA, dance::PIN_I2C_SCL);
  return false;
}

void update() {}

}  // namespace imu
