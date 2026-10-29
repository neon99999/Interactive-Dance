// Wearable firmware entry point: boot, identify, start each module, then run
// the modules' update loops. The IMU and the ESP-NOW link are implemented; the
// other modules are placeholders for now (see README.md).

#include <Arduino.h>

#include "battery.h"
#include "button.h"
#include "config.h"
#include "espnow_link.h"
#include "haptic.h"
#include "imu.h"
#include "protocol.h"

namespace {

uint32_t lastHeartbeatMs = 0;

void waitForSerial() {
  const uint32_t start = millis();
  while (!Serial && millis() - start < dance::SERIAL_WAIT_MS) {
    delay(10);
  }
}

void logIdentity() {
  const uint64_t chipId = ESP.getEfuseMac();
  Serial.println();
  Serial.printf("%s v%u.%u\n", dance::FIRMWARE_NAME, dance::FIRMWARE_VERSION_MAJOR, dance::FIRMWARE_VERSION_MINOR);
  Serial.printf("  wearable id %u, protocol v%u\n", dance::WEARABLE_ID, dance::PROTOCOL_VERSION);
  Serial.printf("  chip %s rev %d, %lu MHz, efuse MAC %012llX\n", ESP.getChipModel(), ESP.getChipRevision(),
                static_cast<unsigned long>(ESP.getCpuFreqMHz()), chipId);
}

// The boot log is often printed before a serial monitor is open, so any key
// typed in the monitor prints the identity again.
void replayIdentityOnKeypress() {
  if (!Serial.available()) return;
  while (Serial.available()) Serial.read();
  logIdentity();
}

void logHeartbeat(uint32_t now) {
  Serial.printf("[heartbeat] uptime %lu s, wearable %u, fw v%u.%u, imu ", static_cast<unsigned long>(now / 1000),
                dance::WEARABLE_ID, dance::FIRMWARE_VERSION_MAJOR, dance::FIRMWARE_VERSION_MINOR);
  if (imu::isReady()) {
    Serial.printf("ok at 0x%02X", imu::address());
  } else {
    Serial.print("not found");
  }
  if (espnow_link::isReady()) {
    Serial.printf(", espnow sent %lu failed %lu\n", static_cast<unsigned long>(espnow_link::sentCount()),
                  static_cast<unsigned long>(espnow_link::failedCount()));
  } else {
    Serial.println(", espnow off");
  }
}

}  // namespace

void setup() {
  // The motor must be off before anything else can delay boot.
  haptic::begin();
  Serial.begin(dance::SERIAL_BAUD);
  waitForSerial();
  logIdentity();

  imu::begin();
  button::begin();
  battery::begin();
  espnow_link::begin();
  Serial.println("boot complete");
}

void loop() {
  imu::update();
  button::update();
  battery::update();
  haptic::update();
  espnow_link::update();
  replayIdentityOnKeypress();

  const uint32_t now = millis();
  if (now - lastHeartbeatMs >= dance::HEARTBEAT_LOG_MS) {
    lastHeartbeatMs = now;
    logHeartbeat(now);
  }
  delay(1);
}
