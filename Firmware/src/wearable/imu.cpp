#include "imu.h"

#include <Arduino.h>
#include <Wire.h>

#include "config.h"

namespace imu {

namespace {

// LSM6DS3TR-C registers (datasheet DocID030071).
constexpr uint8_t REG_WHO_AM_I = 0x0F;
constexpr uint8_t REG_CTRL1_XL = 0x10;
constexpr uint8_t REG_CTRL2_G = 0x11;
constexpr uint8_t REG_CTRL3_C = 0x12;
constexpr uint8_t REG_STATUS = 0x1E;
constexpr uint8_t REG_OUTX_L_G = 0x22;  // gyro X/Y/Z then accel X/Y/Z, 12 bytes
constexpr uint8_t WHO_AM_I_VALUE = 0x6A;

constexpr uint8_t CTRL3_SW_RESET = 0x01;
constexpr uint8_t CTRL3_BDU_IF_INC = 0x44;  // block data update + address auto-increment
constexpr uint8_t CTRL1_XL_104HZ_4G = 0x48;
constexpr uint8_t CTRL2_G_104HZ_2000DPS = 0x4C;
constexpr float ACCEL_G_PER_LSB = 0.000122f;  // +-4 g
constexpr float GYRO_DPS_PER_LSB = 0.070f;    // +-2000 dps

uint8_t sensorAddress = 0;
Reading reading = {};
uint32_t lastReadMs = 0;
uint32_t lastLogMs = 0;
uint32_t lastRetryMs = 0;

bool writeRegister(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(sensorAddress);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool readRegisters(uint8_t addr, uint8_t reg, uint8_t* out, size_t count) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(addr, count) != count) return false;
  for (size_t i = 0; i < count; ++i) out[i] = Wire.read();
  return true;
}

void scanBus() {
  Serial.print("[imu] I2C devices:");
  int found = 0;
  for (uint8_t addr = 1; addr < 127; ++addr) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.printf(" 0x%02X", addr);
      ++found;
    }
  }
  Serial.println(found ? "" : " none (check VIN, GND, SDA and SCL)");
}

// The configured address first, then the other one the LSM6DS3TR-C can use.
bool detect() {
  const uint8_t candidates[] = {dance::IMU_I2C_ADDRESS, dance::IMU_I2C_ADDRESS == 0x6A ? uint8_t(0x6B) : uint8_t(0x6A)};
  for (uint8_t addr : candidates) {
    uint8_t who = 0;
    if (!readRegisters(addr, REG_WHO_AM_I, &who, 1)) continue;
    if (who != WHO_AM_I_VALUE) {
      Serial.printf("[imu] device at 0x%02X answers WHO_AM_I 0x%02X, expected 0x%02X; not an LSM6DS3TR-C\n", addr,
                    who, WHO_AM_I_VALUE);
      continue;
    }
    sensorAddress = addr;
    return true;
  }
  return false;
}

bool configure() {
  if (!writeRegister(REG_CTRL3_C, CTRL3_SW_RESET)) return false;
  delay(20);
  return writeRegister(REG_CTRL3_C, CTRL3_BDU_IF_INC) && writeRegister(REG_CTRL1_XL, CTRL1_XL_104HZ_4G) &&
         writeRegister(REG_CTRL2_G, CTRL2_G_104HZ_2000DPS);
}

bool start() {
  sensorAddress = 0;
  if (!detect()) return false;
  if (!configure()) {
    Serial.printf("[imu] LSM6DS3TR-C at 0x%02X did not accept its settings\n", sensorAddress);
    sensorAddress = 0;
    return false;
  }
  Serial.printf("[imu] LSM6DS3TR-C ready at 0x%02X: 104 Hz, +-4 g, +-2000 dps\n", sensorAddress);
  return true;
}

int16_t toInt16(const uint8_t* bytes) { return static_cast<int16_t>(bytes[0] | (bytes[1] << 8)); }

bool readSensor() {
  uint8_t status = 0;
  if (!readRegisters(sensorAddress, REG_STATUS, &status, 1)) return false;
  if ((status & 0x03) == 0) return true;  // no new accel or gyro sample yet
  uint8_t raw[12];
  if (!readRegisters(sensorAddress, REG_OUTX_L_G, raw, sizeof(raw))) return false;
  reading.gx = toInt16(raw + 0) * GYRO_DPS_PER_LSB;
  reading.gy = toInt16(raw + 2) * GYRO_DPS_PER_LSB;
  reading.gz = toInt16(raw + 4) * GYRO_DPS_PER_LSB;
  reading.ax = toInt16(raw + 6) * ACCEL_G_PER_LSB;
  reading.ay = toInt16(raw + 8) * ACCEL_G_PER_LSB;
  reading.az = toInt16(raw + 10) * ACCEL_G_PER_LSB;
  reading.timeMs = millis();
  return true;
}

}  // namespace

bool begin() {
  Wire.begin(dance::PIN_I2C_SDA, dance::PIN_I2C_SCL, dance::I2C_CLOCK_HZ);
  Serial.printf("[imu] I2C on SDA %d, SCL %d\n", dance::PIN_I2C_SDA, dance::PIN_I2C_SCL);
  scanBus();
  if (start()) return true;
  Serial.printf("[imu] LSM6DS3TR-C not found at 0x6A or 0x6B; retrying every %lu s\n",
                static_cast<unsigned long>(dance::IMU_RETRY_MS / 1000));
  return false;
}

void update() {
  const uint32_t now = millis();
  if (!isReady()) {
    if (now - lastRetryMs >= dance::IMU_RETRY_MS) {
      lastRetryMs = now;
      if (!start()) scanBus();
    }
    return;
  }
  if (now - lastReadMs < dance::IMU_READ_MS) return;
  lastReadMs = now;
  if (!readSensor()) {
    Serial.printf("[imu] lost the sensor at 0x%02X\n", sensorAddress);
    sensorAddress = 0;
    lastRetryMs = now;
    return;
  }
  if (dance::IMU_LOG_MS > 0 && now - lastLogMs >= dance::IMU_LOG_MS) {
    lastLogMs = now;
    Serial.printf("[imu] accel g %6.2f %6.2f %6.2f   gyro dps %8.1f %8.1f %8.1f\n", reading.ax, reading.ay,
                  reading.az, reading.gx, reading.gy, reading.gz);
  }
}

bool isReady() { return sensorAddress != 0; }

uint8_t address() { return sensorAddress; }

const Reading& latest() { return reading; }

}  // namespace imu
