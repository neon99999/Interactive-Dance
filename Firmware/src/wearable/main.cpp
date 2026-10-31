// Wearable firmware entry point: boot, identify, start each module, then run
// the modules' update loops: the IMU, motion processing, wearing mode, button,
// motor, battery and ESP-NOW link (see README.md).
//
// Keys typed in a USB serial monitor:
//   w / a  wrist / ankle mode
//   r      start or stop recording: every sample as a #rec line (below)
//   m      a numbered #mark line in the recording, e.g. before each move
//   other  print the identity again

#include <Arduino.h>

#include "battery.h"
#include "button.h"
#include "config.h"
#include "espnow_link.h"
#include "haptic.h"
#include "imu.h"
#include "mode.h"
#include "motion.h"
#include "protocol.h"

namespace {

uint32_t lastHeartbeatMs = 0;
uint32_t lastLogMs = 0;
bool recording = false;
uint16_t markCount = 0;

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
  Serial.printf("  wearable id %u, protocol v%u, %s mode\n", dance::WEARABLE_ID, dance::PROTOCOL_VERSION,
                mode::settings().name);
  Serial.printf("  chip %s rev %d, %lu MHz, efuse MAC %012llX\n", ESP.getChipModel(), ESP.getChipRevision(),
                static_cast<unsigned long>(ESP.getCpuFreqMHz()), chipId);
  Serial.println("  keys: w wrist, a ankle, r record on/off, m mark");
}

// Recording: lines start with # so TouchDesigner ignores them. Each #rec line
// is one sample: the raw sensor reading, then what the firmware made of it,
// so tools/motion_model.py can be checked against the firmware.
void setRecording(bool on) {
  recording = on;
  if (on) {
    markCount = 0;
    Serial.printf("#rec start, fw v%u.%u, wearable %u, mode %s, body axes %d %d %d\n", dance::FIRMWARE_VERSION_MAJOR,
                  dance::FIRMWARE_VERSION_MINOR, dance::WEARABLE_ID, mode::settings().name, dance::BODY_FORWARD_AXIS,
                  dance::BODY_LEFT_AXIS, dance::BODY_UP_AXIS);
    Serial.println("#rec columns: us,ms,ax,ay,az,gx,gy,gz (sensor axes, raw),pitch,roll,act,hit,dir,still");
  } else {
    Serial.println("#rec stop");
  }
}

void handleKeys() {
  while (Serial.available()) {
    const int key = Serial.read();
    if (key == 'w') {
      mode::set(dance::Mode::Wrist);
    } else if (key == 'a') {
      mode::set(dance::Mode::Ankle);
    } else if (key == 'r') {
      setRecording(!recording);
    } else if (key == 'm') {
      Serial.printf("#mark %u\n", ++markCount);
    } else if (key != '\r' && key != '\n') {
      logIdentity();
    }
  }
}

void logHeartbeat(uint32_t now) {
  Serial.printf("[heartbeat] uptime %lu s, wearable %u, fw v%u.%u, %s, imu ", static_cast<unsigned long>(now / 1000),
                dance::WEARABLE_ID, dance::FIRMWARE_VERSION_MAJOR, dance::FIRMWARE_VERSION_MINOR,
                mode::settings().name);
  if (imu::isReady()) {
    const motion::State& m = motion::state();
    Serial.printf("ok at 0x%02X, gyro %s, hits %u", imu::address(), m.gyroCalibrated ? "calibrated" : "NOT calibrated",
                  m.hits);
  } else {
    Serial.print("not found");
  }
  if (battery::hasReading()) {
    Serial.printf(", battery %u mV %u%%", battery::millivolts(), battery::percent());
  } else {
    Serial.print(", battery no reading");
  }
  if (espnow_link::isReady()) {
    Serial.printf(", espnow sent %lu failed %lu\n", static_cast<unsigned long>(espnow_link::sentCount()),
                  static_cast<unsigned long>(espnow_link::failedCount()));
  } else {
    Serial.println(", espnow off");
  }
}

void logRecordLine() {
  const imu::Reading& r = imu::latest();
  const motion::State& m = motion::state();
  Serial.printf("#rec,%lu,%lu,%.4f,%.4f,%.4f,%.2f,%.2f,%.2f,%.1f,%.1f,%.3f,%u,%u,%u\n",
                static_cast<unsigned long>(r.timeUs), static_cast<unsigned long>(r.timeMs), r.ax, r.ay, r.az, r.gx,
                r.gy, r.gz, m.pitch, m.roll, m.activity, m.hit ? 1 : 0, static_cast<unsigned>(m.hitDirection),
                m.still ? 1 : 0);
}

// One name=value line for TouchDesigner over USB (Read Serial on, 115200),
// read as serial_ax ... serial_mode. The receiver prints the same names with
// a w<id>_ prefix.
void logReading(uint32_t now) {
  if (dance::IMU_LOG_MS == 0 || now - lastLogMs < dance::IMU_LOG_MS) return;
  lastLogMs = now;
  const motion::State& m = motion::state();
  Serial.printf("ax=%.3f ay=%.3f az=%.3f gx=%.1f gy=%.1f gz=%.1f pitch=%.1f roll=%.1f act=%.3f hit=%u hitdir=%u "
                "still=%u btn=%u mode=%u\n",
                m.ax, m.ay, m.az, m.gx, m.gy, m.gz, m.pitch, m.roll, m.activity, m.hit ? 1 : 0,
                static_cast<unsigned>(m.hitDirection), m.still ? 1 : 0, button::isPressed() ? 1 : 0,
                static_cast<unsigned>(mode::current()));
}

}  // namespace

void setup() {
  // The motor must be off before anything else can delay boot.
  haptic::begin();
  // USB serial must never hold up the loop. When the USB cable is plugged in
  // but no program has the port open, each print would otherwise wait for
  // the buffer to empty, and the radio would only send in bursts.
  Serial.setTxBufferSize(4096);  // room for recording at 208 lines a second
  Serial.setTxTimeoutMs(0);
  Serial.begin(dance::SERIAL_BAUD);
  waitForSerial();
  mode::begin();
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
    if (recording) {
      logRecordLine();
    } else {
      logReading(now);
    }
  }
  button::update();
  battery::update();
  haptic::update();
  handleKeys();

  if (!recording && now - lastHeartbeatMs >= dance::HEARTBEAT_LOG_MS) {
    lastHeartbeatMs = now;
    logHeartbeat(now);
  }
  delay(1);
}
