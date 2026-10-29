// Wearable firmware entry point: boot, identify, start each module, then run
// the modules' update loops. The IMU, motion processing and the ESP-NOW link
// are implemented; the other modules are placeholders for now (see README.md).

#include <Arduino.h>

#include "battery.h"
#include "button.h"
#include "config.h"
#include "espnow_link.h"
#include "haptic.h"
#include "imu.h"
#include "motion.h"
#include "protocol.h"

namespace {

uint32_t lastHeartbeatMs = 0;
uint32_t lastLogMs = 0;

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
    const motion::State& m = motion::state();
    Serial.printf("ok at 0x%02X, gyro %s, hits %u", imu::address(), m.gyroCalibrated ? "calibrated" : "NOT calibrated",
                  m.hits);
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

// One name=value line for TouchDesigner over USB (Read Serial on, 115200),
// read as serial_ax ... serial_hit. The receiver prints the same names with
// a w<id>_ prefix.
void logReading(uint32_t now) {
  if (dance::IMU_LOG_MS == 0 || now - lastLogMs < dance::IMU_LOG_MS) return;
  lastLogMs = now;
  const imu::Reading& r = imu::latest();
  const motion::State& m = motion::state();
  Serial.printf("ax=%.3f ay=%.3f az=%.3f gx=%.1f gy=%.1f gz=%.1f pitch=%.1f roll=%.1f act=%.3f hit=%u\n", r.ax, r.ay,
                r.az, m.gx, m.gy, m.gz, m.pitch, m.roll, m.activity, m.hit ? 1 : 0);
}

}  // namespace

void setup() {
  // The motor must be off before anything else can delay boot.
  haptic::begin();
  // USB serial must never hold up the loop. When the USB cable is plugged in
  // but no program has the port open, each print would otherwise wait for
  // the buffer to empty, and the radio would only send in bursts.
  Serial.setTxBufferSize(1024);
  Serial.setTxTimeoutMs(0);
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
  const uint32_t now = millis();
  if (imu::update()) {
    motion::update(imu::latest());
    espnow_link::update();  // send first: the radio is the low-latency path
    logReading(now);
  }
  button::update();
  battery::update();
  haptic::update();
  replayIdentityOnKeypress();

  if (now - lastHeartbeatMs >= dance::HEARTBEAT_LOG_MS) {
    lastHeartbeatMs = now;
    logHeartbeat(now);
  }
  delay(1);
}
