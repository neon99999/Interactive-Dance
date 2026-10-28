// IMU: Adafruit LSM6DS3TR-C accelerometer + gyroscope over I2C.
// Placeholder: begin() only logs. Later: start Wire on PIN_I2C_SDA/SCL, detect
// the sensor at IMU_I2C_ADDRESS, and read acceleration and rotation in update().
#pragma once

namespace imu {
bool begin();
void update();
}  // namespace imu
