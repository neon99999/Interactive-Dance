// Receiver firmware entry point (LOLIN NodeMCU V3, ESP8266).
//
// Listens for protocol.h packets over ESP-NOW and forwards each wearable's
// motion to TouchDesigner as one serial line of name=value pairs:
//   w1_ax=0.012 w1_ay=-0.021 w1_az=1.003 w1_gx=0.4 w1_gy=-0.3 w1_gz=0.1
//   w1_pitch=-1.2 w1_roll=0.8 w1_act=0.031 w1_hit=0 w1_hitdir=0 w1_still=1
//   w1_btn=0 w1_mode=1
// which inputs > Serial reads as serial_w1_ax ... serial_w1_mode. Wearables
// on fw v0.4-v0.5 (protocol v2) send no motion processing, so their lines
// stop after w1_gz. When a wearable appears or goes quiet it also prints
// w1_live=1 or w1_live=0; going quiet also sets act, hit, still and btn to 0,
// so nothing is left switched on. Log lines start with [ so TouchDesigner
// ignores them. The display shows the same state.
//
// Latency first: every loop pass forwards all waiting packets before the
// display draws one small piece, so a redraw never holds a line back for
// more than a few milliseconds.

#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <stdlib.h>
#include <string.h>

#include "display.h"
#include "protocol.h"
#include "radio.h"
#include "receiver_config.h"
#include "wearables.h"

namespace rx {
Wearable wearables[MAX_WEARABLES];
Totals totals;
}  // namespace rx

namespace {

uint32_t lastSecondMs = 0;
uint32_t lastHeartbeatMs = 0;

void logIdentity() {
  Serial.println();
  Serial.printf("[rx] %s v%u.%u, protocol v%u (accepts v%u-v%u), channel %u\n", rx::FIRMWARE_NAME,
                rx::FIRMWARE_VERSION_MAJOR, rx::FIRMWARE_VERSION_MINOR, dance::PROTOCOL_VERSION,
                dance::PROTOCOL_VERSION_OLDEST, dance::PROTOCOL_VERSION, dance::ESPNOW_CHANNEL);
  Serial.printf("[rx] chip ESP8266 id %06X, %u MHz, MAC %s\n", ESP.getChipId(), ESP.getCpuFreqMHz(),
                WiFi.macAddress().c_str());
}

// Any key typed in a serial monitor prints the identity again (the boot log
// is usually gone by the time a monitor opens).
void replayIdentityOnKeypress() {
  if (!Serial.available()) return;
  while (Serial.available()) Serial.read();
  logIdentity();
}

// Appends "w<id>_<name>=<value> " with a fixed-point value, e.g. 1003 with 3
// decimals -> 1.003. Integer formatting only, so no printf float support is needed.
char* appendValue(char* out, uint8_t id, const char* name, int value, int decimals) {
  const unsigned scale = decimals == 3 ? 1000 : 10;
  const unsigned magnitude = static_cast<unsigned>(abs(value));
  return out + sprintf(out, "w%u_%s=%s%u.%0*u ", id, name, value < 0 ? "-" : "", magnitude / scale, decimals,
                       magnitude % scale);
}

void printMotion(uint8_t id, const rx::Wearable& w) {
  char line[240];
  char* p = line;
  p = appendValue(p, id, "ax", w.ax, 3);
  p = appendValue(p, id, "ay", w.ay, 3);
  p = appendValue(p, id, "az", w.az, 3);
  p = appendValue(p, id, "gx", w.gx, 1);
  p = appendValue(p, id, "gy", w.gy, 1);
  p = appendValue(p, id, "gz", w.gz, 1);
  if (w.hasMotion) {
    p = appendValue(p, id, "pitch", w.pitch, 1);
    p = appendValue(p, id, "roll", w.roll, 1);
    p = appendValue(p, id, "act", w.activity, 3);  // MOTION_ACTIVITY_FULL is 1000
    p += sprintf(p, "w%u_hit=%u w%u_hitdir=%u w%u_still=%u w%u_btn=%u w%u_mode=%u ", id, w.hit ? 1 : 0, id,
                 w.hitDirection, id, w.still ? 1 : 0, id, w.button ? 1 : 0, id, w.mode);
  }
  p[-1] = '\n';  // replaces the last trailing space
  Serial.write(line, p - line);
}

void setLive(uint8_t id, rx::Wearable& w, bool live) {
  if (w.live == live) return;
  w.live = live;
  if (live) {
    Serial.printf("w%u_live=1\n", id);
  } else {
    w.activity = 0;
    w.hit = w.still = w.button = false;
    if (w.hasMotion) {
      Serial.printf("w%u_live=0 w%u_act=0 w%u_hit=0 w%u_still=0 w%u_btn=0\n", id, id, id, id, id);
    } else {
      Serial.printf("w%u_live=0\n", id);
    }
  }
  Serial.printf("[rx] wearable %u %s\n", id, live ? "connected" : "lost");
}

// Two devices flashed with the same id would mix their readings and wreck
// the sequence count. While a wearable is live, a packet from another MAC
// address marks the id as shared.
void checkSender(uint8_t id, rx::Wearable& w, const uint8_t* mac, uint32_t now) {
  if (w.seen && w.live && memcmp(w.mac, mac, sizeof(w.mac)) != 0) {
    if (!w.duplicateSeen || now - w.duplicateMs > rx::DUPLICATE_SHOW_MS) {
      Serial.printf("[rx] wearable %u: two devices use this id (%02X:%02X:%02X:%02X:%02X:%02X and "
                    "%02X:%02X:%02X:%02X:%02X:%02X); flash one with another id\n",
                    id, w.mac[0], w.mac[1], w.mac[2], w.mac[3], w.mac[4], w.mac[5], mac[0], mac[1], mac[2], mac[3],
                    mac[4], mac[5]);
    }
    w.duplicateSeen = true;
    w.duplicateMs = now;
  }
  memcpy(w.mac, mac, sizeof(w.mac));
}

// Reads the packet into w; false when its type or length is wrong.
bool readPacket(const radio::RawPacket& raw, dance::PacketType type, uint8_t version, uint8_t id,
                rx::Wearable& w) {
  if (type == dance::PacketType::Hello && raw.length == sizeof(dance::HelloPacket)) {
    dance::HelloPacket hello;
    memcpy(&hello, raw.data, sizeof(hello));
    // Wearables from v0.8 repeat their Hello every 2 s: log only a new version.
    const bool changed = hello.firmwareMajor != w.firmwareMajor || hello.firmwareMinor != w.firmwareMinor;
    w.firmwareMajor = hello.firmwareMajor;
    w.firmwareMinor = hello.firmwareMinor;
    if (!changed) return true;
    Serial.printf("[rx] wearable %u says hello: fw v%u.%u, protocol v%u, MAC %02X:%02X:%02X:%02X:%02X:%02X\n", id,
                  hello.firmwareMajor, hello.firmwareMinor, version, raw.mac[0], raw.mac[1], raw.mac[2], raw.mac[3],
                  raw.mac[4], raw.mac[5]);
    return true;
  }
  if (type != dance::PacketType::Motion) return false;
  if (version == 2 && raw.length == sizeof(dance::MotionPacketV2)) {
    dance::MotionPacketV2 motion;
    memcpy(&motion, raw.data, sizeof(motion));
    w.ax = motion.ax, w.ay = motion.ay, w.az = motion.az;
    w.gx = motion.gx, w.gy = motion.gy, w.gz = motion.gz;
    w.hasMotion = false;
    return true;
  }
  if (version >= 3 && raw.length == sizeof(dance::MotionPacket)) {
    dance::MotionPacket motion;
    memcpy(&motion, raw.data, sizeof(motion));
    w.ax = motion.ax, w.ay = motion.ay, w.az = motion.az;
    w.gx = motion.gx, w.gy = motion.gy, w.gz = motion.gz;
    w.pitch = motion.pitch;
    w.roll = motion.roll;
    w.activity = motion.activity;
    w.hit = motion.flags & dance::MOTION_FLAG_HIT;
    w.still = motion.flags & dance::MOTION_FLAG_STILL;
    w.button = motion.flags & dance::MOTION_FLAG_BUTTON;
    w.gyroCalibrated = motion.flags & dance::MOTION_FLAG_GYRO_CALIBRATED;
    w.hitDirection = motion.hitDirection;
    w.hits = motion.hits;
    w.mode = motion.mode;
    w.hasMotion = true;
    return true;
  }
  return false;
}

void handlePacket(const radio::RawPacket& raw, uint32_t now) {
  dance::PacketHeader header;
  if (raw.length < sizeof(header)) {
    ++rx::totals.badPackets;
    return;
  }
  memcpy(&header, raw.data, sizeof(header));
  if (!dance::isValidHeader(header) || header.wearableId < 1 || header.wearableId > rx::MAX_WEARABLES) {
    ++rx::totals.badPackets;
    return;
  }
  const uint8_t id = header.wearableId;
  rx::Wearable& w = rx::wearables[id - 1];
  const auto type = static_cast<dance::PacketType>(header.type);
  if (!readPacket(raw, type, header.version, id, w)) {
    ++rx::totals.badPackets;
    return;
  }
  // Printed before any bookkeeping: this line is what TouchDesigner waits for.
  if (type == dance::PacketType::Motion) printMotion(id, w);

  checkSender(id, w, raw.mac, now);
  w.protocolVersion = header.version;
  // Count gaps in the sequence. A big jump means the wearable restarted.
  const uint16_t gap = header.sequence - w.lastSequence;
  if (w.seen && gap > 1 && gap < 1000) {
    w.lost += gap - 1;
    w.lostThisSecond += gap - 1;
  }
  w.seen = true;
  w.lastSequence = header.sequence;
  w.lastPacketMs = now;
  ++w.packets;
  ++w.packetsThisSecond;
  setLive(id, w, true);
}

void everySecond(uint32_t now) {
  if (now - lastSecondMs < 1000) return;
  lastSecondMs = now;
  for (uint8_t i = 0; i < rx::MAX_WEARABLES; ++i) {
    rx::Wearable& w = rx::wearables[i];
    w.ratePerSecond = w.packetsThisSecond;
    w.packetsThisSecond = 0;
    w.lostPerSecond = w.lostThisSecond;
    w.lostThisSecond = 0;
    if (w.live && now - w.lastPacketMs > rx::LOST_AFTER_MS) setLive(i + 1, w, false);
  }
}

void logHeartbeat(uint32_t now) {
  if (now - lastHeartbeatMs < rx::HEARTBEAT_LOG_MS) return;
  lastHeartbeatMs = now;
  Serial.printf("[heartbeat] uptime %lu s, rx fw v%u.%u, channel %u, bad %lu, dropped %lu",
                static_cast<unsigned long>(now / 1000),
                rx::FIRMWARE_VERSION_MAJOR, rx::FIRMWARE_VERSION_MINOR, dance::ESPNOW_CHANNEL,
                static_cast<unsigned long>(rx::totals.badPackets), static_cast<unsigned long>(radio::droppedCount()));
  for (uint8_t i = 0; i < rx::MAX_WEARABLES; ++i) {
    const rx::Wearable& w = rx::wearables[i];
    if (!w.seen) continue;
    Serial.printf(", w%u %s %u/s lost %lu hits %u%s", i + 1, w.live ? "live" : "LOST", w.ratePerSecond,
                  static_cast<unsigned long>(w.lost), w.hits,
                  w.duplicateSeen && now - w.duplicateMs < rx::DUPLICATE_SHOW_MS ? " DUPLICATE ID" : "");
  }
  Serial.println();
}

}  // namespace

void setup() {
  Serial.begin(rx::SERIAL_BAUD);
  delay(100);
  logIdentity();
  display::begin();
  if (!radio::begin(dance::ESPNOW_CHANNEL)) Serial.println("[rx] radio failed to start; nothing will be received");
  Serial.println("[rx] boot complete");
}

void loop() {
  const uint32_t now = millis();
  radio::RawPacket raw;
  while (radio::pop(raw)) handlePacket(raw, now);
  everySecond(now);
  logHeartbeat(now);
  replayIdentityOnKeypress();
  display::update(now);  // one small piece per pass
  yield();
}
